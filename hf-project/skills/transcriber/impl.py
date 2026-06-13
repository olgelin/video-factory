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
        vad_filter=True,
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


def generate_srt(transcript: dict, output_path: str):
    """生成SRT字幕文件"""
    segments = transcript.get("segments", [])

    srt_content = ""
    for i, seg in enumerate(segments):
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "").strip()

        if not text:
            continue

        start_h, start_r = divmod(start, 3600)
        start_m, start_s = divmod(start_r, 60)
        end_h, end_r = divmod(end, 3600)
        end_m, end_s = divmod(end_r, 60)

        srt_content += f"{i+1}\n"
        srt_content += f"{int(start_h):02d}:{int(start_m):02d}:{start_s:06.3f} --> {int(end_h):02d}:{int(end_m):02d}:{end_s:06.3f}\n"
        srt_content += f"{text}\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"  [transcriber] SRT已保存: {output_path}")


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
