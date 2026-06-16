"""
transcriber/skill.py — faster-whisper时间戳生成
功能：用faster-whisper转录音频，生成精确逐词时间戳
输出：whisperx_transcript.json + captions.srt

v30: 从WhisperX改为faster-whisper（纯CPU，无torchcodec依赖）
"""

import os
import json
from pathlib import Path

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
TRANSCRIPT_PATH = OUTPUT_DIR / "whisperx_transcript.json"
CAPTIONS_PATH = OUTPUT_DIR / "captions.srt"


def run_faster_whisper(audio_path: str) -> dict:
    """用faster-whisper转录音频"""
    from faster_whisper import WhisperModel

    print(f"  [transcriber] Loading faster-whisper (large-v3, CPU)...")
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")

    print(f"  [transcriber] Transcribing: {audio_path}")
    segments_gen, info = model.transcribe(
        audio_path,
        language="zh",
        beam_size=5,
        word_timestamps=True,
        vad_filter=False,
    )

    segments = []
    for seg in segments_gen:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({
                    "word": w.word,
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "probability": round(w.probability, 3),
                })
        segments.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": words,
        })

    transcript = {
        "segments": segments,
        "language": info.language,
        "duration": info.duration,
    }

    print(f"  [transcriber] ✅ 转录完成: {len(segments)} segments, {info.duration:.1f}s")
    return transcript


def _format_srt_time(seconds: float) -> str:
    """格式化SRT时间戳"""
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def generate_srt(transcript: dict, output_path: str, max_chars: int = 18, max_duration: float = 4.0):
    """生成SRT字幕文件
    
    关键改进：
    1. 长文本拆分为每行最多max_chars字
    2. 每条字幕最多max_duration秒
    3. 确保时间线连续无缺口
    """
    segments = transcript.get("segments", [])
    
    # 第一步：拆分长segment为短条目
    entries = []
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "").strip()
        if not text:
            continue
        
        dur = end - start
        if dur <= 0:
            continue
        
        # 如果文本短且时长合理，直接使用
        if len(text) <= max_chars and dur <= max_duration:
            entries.append({"start": start, "end": end, "text": text})
            continue
        
        # 拆分长文本：按max_chars分段
        chunks = []
        while text:
            if len(text) <= max_chars:
                chunks.append(text)
                break
            # 找最近的标点或空格断行
            cut = max_chars
            for punct in "，。、；！？,.;!? ":
                idx = text[:max_chars].rfind(punct)
                if idx > max_chars // 2:
                    cut = idx + 1
                    break
            chunks.append(text[:cut].strip())
            text = text[cut:].strip()
        
        if not chunks:
            continue
        
        # 按字数比例分配时间
        total_chars = sum(len(c) for c in chunks)
        current_start = start
        for chunk in chunks:
            chunk_dur = dur * len(chunk) / total_chars if total_chars > 0 else dur / len(chunks)
            chunk_dur = max(chunk_dur, 0.5)  # 最少0.5秒
            current_end = min(current_start + chunk_dur, end)
            entries.append({"start": current_start, "end": current_end, "text": chunk})
            current_start = current_end
    
    if not entries:
        print(f"  ⚠️ [transcriber] 无有效字幕条目")
        return
    
    # 第二步：修复时间线（填补缺口，消除重叠）
    entries.sort(key=lambda e: e["start"])
    for i in range(len(entries)):
        # 与前一条对齐（填补缺口）
        if i > 0:
            gap = entries[i]["start"] - entries[i-1]["end"]
            if 0 < gap < 2.0:
                # 小缺口：延伸前一条的结束时间
                entries[i-1]["end"] = entries[i]["start"]
            elif gap < 0:
                # 重叠：截断前一条
                entries[i-1]["end"] = entries[i]["start"]
        
        # 限制单条时长
        if entries[i]["end"] - entries[i]["start"] > max_duration:
            entries[i]["end"] = entries[i]["start"] + max_duration
    
    # 第三步：生成SRT
    srt_content = ""
    for i, entry in enumerate(entries):
        srt_content += f"{i+1}\n"
        srt_content += f"{_format_srt_time(entry['start'])} --> {_format_srt_time(entry['end'])}\n"
        srt_content += f"{entry['text']}\n\n"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
    
    print(f"  [transcriber] SRT已保存: {output_path} ({len(entries)} 条)")


def run(context: dict) -> dict:
    """主入口：转录音频"""

    voice_path = context.get("voice_path") or str(OUTPUT_DIR / "step05_voice.wav")
    if not os.path.exists(voice_path):
        print(f"  ❌ [transcriber] 找不到音频: {voice_path}")
        return context

    print(f"  [transcriber] 转录: {voice_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    transcript = run_faster_whisper(voice_path)

    if not transcript or not transcript.get("segments"):
        print(f"  ❌ [transcriber] 转录失败")
        return context

    with open(TRANSCRIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    print(f"  [transcriber] Transcript已保存: {TRANSCRIPT_PATH}")

    generate_srt(transcript, str(CAPTIONS_PATH))

    segments = transcript.get("segments", [])
    total_words = sum(len(seg.get("text", "")) for seg in segments)
    duration = segments[-1].get("end", 0) if segments else 0

    print(f"  [transcriber] ✅ 转录完成: {len(segments)} 个片段, {total_words} 字, {duration:.1f}s")

    context["transcript_path"] = str(TRANSCRIPT_PATH)
    context["captions_path"] = str(CAPTIONS_PATH)
    context["transcript_data"] = transcript

    return context


if __name__ == "__main__":
    test_context = {
        "voice_path": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/output/step05_voice.wav",
    }
    result = run(test_context)
