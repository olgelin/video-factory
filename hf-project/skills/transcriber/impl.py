"""
transcriber/impl.py — 语音转录 V4（工具隔离版）
通过tool_runner调用独立venv中的FunASR CLI
"""

import os
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
TRANSCRIPT_PATH = OUTPUT_DIR / "whisperx_transcript.json"
SRT_PATH = OUTPUT_DIR / "captions.srt"


def run(context: dict) -> dict:
    """主入口：通过subprocess调用Transcriber"""

    # 读取配音文件
    voice_path = context.get("voice_path") or str(OUTPUT_DIR / "step05_voice.wav")
    if not os.path.exists(voice_path):
        print(f"  ❌ [transcriber] 找不到配音: {voice_path}")
        return context

    print(f"  [transcriber] 音频: {voice_path}")

    # 输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 通过tool_runner调用Transcriber CLI
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from tool_runner import call_transcriber

    result = call_transcriber(
        input_path=voice_path,
        output_path=str(TRANSCRIPT_PATH),
        srt_path=str(SRT_PATH),
    )

    if result.get("error"):
        print(f"  ❌ [transcriber] 失败: {result['error']}")
        # fallback：用voice_scene_durations生成近似transcript
        print(f"  [transcriber] 尝试fallback方案...")
        return _fallback_from_voice_durations(context)

    # === V5.2 Fix A: FunASR质量检测 ===
    # 即使FunASR返回成功，如果80%+文本挤在一个segment里，视为失败
    segments = result.get("segments", [])
    if isinstance(segments, list) and len(segments) > 0:
        total_text_len = sum(len(s.get("text", "").strip()) for s in segments)
        if total_text_len > 0:
            max_seg_len = max(len(s.get("text", "").strip()) for s in segments)
            concentration = max_seg_len / total_text_len
            if concentration > 0.8:
                print(f"  ⚠️ [transcriber] FunASR质量差: {concentration:.0%}文本集中在1个segment "
                      f"({max_seg_len}/{total_text_len} chars)，触发fallback")
                return _fallback_from_voice_durations(context)

    # 更新context
    context["transcript_path"] = str(TRANSCRIPT_PATH)
    context["srt_path"] = str(SRT_PATH)
    context["transcript_duration"] = result.get("duration", 0)
    context["transcript_segments"] = result.get("segments", 0)

    print(f"  [transcriber] ✅ 转录完成: {result.get('segments', 0)} segments, {result.get('duration', 0):.1f}s")
    return context


def _fallback_from_voice_durations(context: dict) -> dict:
    """V5.3: 用 voice_scene_durations 生成 transcript + SRT
    改进：使用 voice_gen 的真实 segment 时长，而非按字符数均匀分配"""
    vsd_path = OUTPUT_DIR / "voice_scene_durations.json"
    if not vsd_path.exists():
        print(f"  ❌ [transcriber] fallback也失败: voice_scene_durations.json不存在")
        return context

    with open(vsd_path, "r", encoding="utf-8") as f:
        voice_durations = json.load(f)

    # 从script读取文本
    script_path = context.get("script_path") or str(OUTPUT_DIR / "step03_script.json")
    sections = []
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)
        sections = script_data.get("voiceover_sections", script_data.get("scenes", []))

    segments = []
    cumulative = 0.0
    for i, vsd in enumerate(voice_durations):
        dur = vsd.get("duration", 5.0)
        text = ""
        if i < len(sections):
            text = sections[i].get("content", "") or sections[i].get("voiceover", "") or sections[i].get("text", "")
        if not text:
            text = vsd.get("text", f"段落{i+1}")

        # V5.3: 使用 voice_gen 的真实时长作为 segment 边界
        # 不再按字符数均匀分配，而是每个 scene 一个 segment
        segments.append({
            "start": round(cumulative, 3),
            "end": round(cumulative + dur, 3),
            "text": text,
            "words": [],
        })
        cumulative += dur

    transcript = {
        "segments": segments,
        "language": "zh",
        "duration": cumulative,
    }

    with open(TRANSCRIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)

    context["transcript_path"] = str(TRANSCRIPT_PATH)
    context["transcript_duration"] = cumulative
    context["transcript_segments"] = len(segments)

    # V5.3: 生成 SRT — 每个 scene 的文本按标点拆分为多行，时间按真实时长分配
    _generate_srt_from_segments_v2(segments, str(SRT_PATH))
    context["srt_path"] = str(SRT_PATH)

    print(f"  [transcriber] ✅ fallback完成: {len(segments)} segments, {cumulative:.1f}s, SRT已生成")
    return context


def _generate_srt_from_segments_v2(segments: list, output_path: str, max_chars: int = 18):
    """V5.3: 从 transcript segments 生成 SRT — 使用真实 segment 时间边界"""
    entries = []
    for seg in segments:
        text = seg.get("text", "").strip()
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        if not text or end <= start:
            continue

        # 按标点拆分为短行
        remaining = text
        seg_start = start
        seg_dur = end - start
        # 先按标点拆分
        import re
        chunks = re.split(r'(?<=[。！？，；、])', remaining)
        chunks = [c.strip() for c in chunks if c.strip()]
        
        if not chunks:
            chunks = [remaining]
        
        # 合并过短的 chunk，拆分过长的 chunk
        merged = []
        buf = ""
        for c in chunks:
            if len(buf) + len(c) <= max_chars:
                buf += c
            else:
                if buf:
                    merged.append(buf)
                buf = c
        if buf:
            merged.append(buf)
        
        # 分配时间
        total_chars = sum(len(c) for c in merged)
        for j, chunk in enumerate(merged):
            chunk_dur = seg_dur * len(chunk) / max(total_chars, 1)
            chunk_end = min(seg_start + max(chunk_dur, 0.8), end)
            entries.append({"start": seg_start, "end": chunk_end, "text": chunk})
            seg_start = chunk_end

    # 写入 SRT
    srt_content = ""
    for i, entry in enumerate(entries):
        srt_content += f"{i+1}\n"
        srt_content += f"{_format_srt_time(entry['start'])} --> {_format_srt_time(entry['end'])}\n"
        srt_content += f"{entry['text']}\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"  [transcriber] SRT已保存: {output_path} ({len(entries)} 条, 覆盖 {segments[-1]['end']:.1f}s)")


def _format_srt_time(seconds: float) -> str:
    """格式化SRT时间戳"""
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


if __name__ == "__main__":
    test_context = {
        "voice_path": str(OUTPUT_DIR / "step05_voice.wav"),
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  转录路径: {result.get('transcript_path')}")
    print(f"  时长: {result.get('transcript_duration')}")
