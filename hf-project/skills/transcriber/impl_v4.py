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

    # 更新context
    context["transcript_path"] = str(TRANSCRIPT_PATH)
    context["srt_path"] = str(SRT_PATH)
    context["transcript_duration"] = result.get("duration", 0)
    context["transcript_segments"] = result.get("segments", 0)

    print(f"  [transcriber] ✅ 转录完成: {result.get('segments', 0)} segments, {result.get('duration', 0):.1f}s")
    return context


def _fallback_from_voice_durations(context: dict) -> dict:
    """用voice_scene_durations生成近似transcript + SRT（ASR不可用时的fallback）"""
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

    # === V5.2: 同时生成 SRT ===
    _generate_srt_from_segments(segments, str(SRT_PATH))
    context["srt_path"] = str(SRT_PATH)

    print(f"  [transcriber] ✅ fallback完成: {len(segments)} segments, {cumulative:.1f}s, SRT已生成")
    return context


def _generate_srt_from_segments(segments: list, output_path: str, max_chars: int = 18):
    """从 transcript segments 生成 SRT 字幕文件（按实际时间戳对齐）"""
    entries = []
    for seg in segments:
        text = seg.get("text", "").strip()
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        if not text or end <= start:
            continue

        remaining = text
        seg_start = start
        seg_dur = end - start
        while remaining:
            if len(remaining) <= max_chars:
                entries.append({"start": seg_start, "end": end, "text": remaining})
                break
            cut = max_chars
            for punct in "，。、；！？,.;!? ":
                idx = remaining[:max_chars].rfind(punct)
                if idx > max_chars // 2:
                    cut = idx + 1
                    break
            chunk = remaining[:cut].strip()
            chunk_dur = seg_dur * len(chunk) / max(len(text), 1)
            chunk_end = min(seg_start + max(chunk_dur, 0.8), end)
            entries.append({"start": seg_start, "end": chunk_end, "text": chunk})
            remaining = remaining[cut:].strip()
            seg_start = chunk_end

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
