#!/usr/bin/env python3
"""
Transcriber 工具 - 独立CLI接口
用法:
  python cli.py --input voice.wav --output transcript.json [--srt-output captions.srt]

输出: transcript JSON + SRT字幕 + stdout输出JSON元数据
"""

import argparse
import json
import os
import sys
from pathlib import Path

# === 环境隔离：只移除hermes-agent/venv的路径 ===
if 'PYTHONPATH' in os.environ:
    del os.environ['PYTHONPATH']
sys.path[:] = [p for p in sys.path if not any(
    x in p.lower() for x in ['hermes-agent\\venv', 'hermes_agent\\venv', 'hermes-agent/venv', 'hermes_agent/venv']
)]

# 纠错字典
_TRANSCRIPTION_CORRECTIONS = {
    "厂长": "场长", "出场厂": "出场场",
}


def _fix_chinese_spacing(text: str) -> str:
    import re
    text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', text)
    text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', text)
    return text.strip()


def _fix_transcription_errors(text: str) -> str:
    for wrong, correct in _TRANSCRIPTION_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    return text


def transcribe_funasr(audio_path: str) -> dict:
    """用FunASR转录"""
    from funasr import AutoModel

    print("[transcriber] Loading FunASR...", file=sys.stderr)
    model = AutoModel(
        model='iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
        model_revision='v2.0.4',
        disable_update=True
    )

    print(f"[transcriber] Transcribing: {audio_path}", file=sys.stderr)
    result = model.generate(input=audio_path, batch_size_s=300)

    if not result:
        return None

    segments = []
    for item in result:
        text = item.get('text', '')
        timestamp = item.get('timestamp', [])

        if timestamp and len(timestamp) >= 2:
            start = timestamp[0][0] / 1000.0
            end = timestamp[-1][1] / 1000.0
        else:
            start = 0
            end = len(text) * 0.15

        segments.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "text": _fix_transcription_errors(_fix_chinese_spacing(text.strip())),
            "words": [],
        })

    total_duration = segments[-1]["end"] if segments else 0

    return {
        "segments": segments,
        "language": "zh",
        "duration": total_duration,
    }


def generate_srt(transcript: dict, output_path: str, max_chars: int = 18):
    """生成SRT字幕"""
    segments = transcript.get("segments", [])
    entries = []
    idx = 1

    for seg in segments:
        text = seg["text"]
        start = seg["start"]
        end = seg["end"]

        if len(text) <= max_chars:
            entries.append({"index": idx, "start": start, "end": end, "text": text})
            idx += 1
        else:
            # 拆分长文本
            chunks = []
            remaining = text
            while remaining:
                if len(remaining) <= max_chars:
                    chunks.append(remaining)
                    break
                cut = max_chars
                for punct in "，。、；！？,.;!? ":
                    idx_p = remaining[:max_chars].rfind(punct)
                    if idx_p > max_chars // 2:
                        cut = idx_p + 1
                        break
                chunks.append(remaining[:cut])
                remaining = remaining[cut:]

            chunk_dur = (end - start) / len(chunks) if chunks else 0
            for j, chunk in enumerate(chunks):
                c_start = start + j * chunk_dur
                c_end = c_start + chunk_dur
                entries.append({"index": idx, "start": c_start, "end": c_end, "text": chunk})
                idx += 1

    # 写SRT
    with open(output_path, "w", encoding="utf-8") as f:
        for e in entries:
            s_h, s_m = int(e["start"] // 3600), int(e["start"] % 3600 // 60)
            s_s, s_ms = int(e["start"] % 60), int((e["start"] % 1) * 1000)
            e_h, e_m = int(e["end"] // 3600), int(e["end"] % 3600 // 60)
            e_s, e_ms = int(e["end"] % 60), int((e["end"] % 1) * 1000)
            f.write(f"{e['index']}\n")
            f.write(f"{s_h:02d}:{s_m:02d}:{s_s:02d},{s_ms:03d} --> {e_h:02d}:{e_m:02d}:{e_s:02d},{e_ms:03d}\n")
            f.write(f"{e['text']}\n\n")

    return len(entries)


def main():
    parser = argparse.ArgumentParser(description="Transcriber CLI")
    parser.add_argument("--input", required=True, help="输入音频文件")
    parser.add_argument("--output", required=True, help="输出transcript JSON")
    parser.add_argument("--srt-output", help="输出SRT字幕文件")
    parser.add_argument("--method", default="funasr", choices=["funasr"], help="转录方法")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(json.dumps({"error": f"音频文件不存在: {args.input}"}))
        sys.exit(1)

    # 转录
    transcript = transcribe_funasr(args.input)

    if not transcript:
        print(json.dumps({"error": "转录失败"}))
        sys.exit(1)

    # 保存transcript
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)

    # 生成SRT
    srt_count = 0
    srt_path = args.srt_output
    if srt_path:
        srt_count = generate_srt(transcript, srt_path)

    # 输出元数据
    print(json.dumps({
        "success": True,
        "transcript_path": args.output,
        "srt_path": srt_path if srt_path else None,
        "segments": len(transcript["segments"]),
        "duration": round(transcript["duration"], 2),
        "srt_entries": srt_count,
    }))


if __name__ == "__main__":
    main()
