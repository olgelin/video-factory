#!/usr/bin/env python3
"""
ACE-Step BGM 工具 - 独立CLI接口
用法:
  python cli.py --lyrics lyrics.txt --output bgm.wav [--duration 120] [--captions "electronic, tech"]

输入: 歌词文件（ACE-Step格式）
输出: WAV文件 + stdout输出JSON元数据
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# === 环境隔离：只移除hermes-agent/venv的路径 ===
if 'PYTHONPATH' in os.environ:
    del os.environ['PYTHONPATH']
sys.path[:] = [p for p in sys.path if not any(
    x in p.lower() for x in ['hermes-agent\\venv', 'hermes_agent\\venv', 'hermes-agent/venv', 'hermes_agent/venv']
)]

# ACE-Step路径
ACESTEP_ROOT = os.environ.get("ACESTEP_ROOT", "E:/Hermes-Agent/workspace/xiaoshan/models/acestep_package")
ACESTEP_CHECKPOINT = os.environ.get("ACESTEP_CHECKPOINT", "acestep-v15-turbo")

# acestep_package是本地包，需要添加父目录到sys.path
sys.path.insert(0, str(Path(ACESTEP_ROOT).parent))


def init_handler():
    """初始化ACE-Step handler"""
    import torch

    for retry in range(5):
        try:
            from acestep_package.handler import AceStepHandler
            break
        except (OSError, ImportError) as e:
            if retry < 4:
                print(f"[acestep] Import retry {retry+1}/5: {e}", file=sys.stderr)
                time.sleep(2)
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            else:
                raise

    for retry in range(3):
        try:
            handler = AceStepHandler()
            break
        except OSError as oe:
            if retry < 2:
                print(f"[acestep] Init retry {retry+1}/3: {oe}", file=sys.stderr)
                time.sleep(3)
            else:
                raise

    for retry in range(3):
        try:
            result = handler.initialize_service(
                project_root=ACESTEP_ROOT,
                config_path=ACESTEP_CHECKPOINT,
                device="cuda" if torch.cuda.is_available() else "cpu",
            )
            break
        except OSError as oe:
            if retry < 2:
                print(f"[acestep] Service retry {retry+1}/3: {oe}", file=sys.stderr)
                time.sleep(3)
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            else:
                raise

    ok = result[1]
    if not ok:
        raise RuntimeError(f"ACE-Step初始化失败: {result[0][:200]}")

    return handler


def generate_bgm(handler, lyrics, output_path, duration=120, captions="electronic, tech, cinematic, 100 BPM"):
    """生成BGM"""
    import torch
    import soundfile as sf

    attempts = [
        {"use_tiled_decode": False, "audio_duration": duration},
        {"use_tiled_decode": True, "audio_duration": duration},
        {"use_tiled_decode": False, "audio_duration": -1},
    ]

    for i, params in enumerate(attempts):
        print(f"[acestep] Attempt {i+1}/3: tiled={params['use_tiled_decode']}, dur={params['audio_duration']}", file=sys.stderr)

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        for gen_retry in range(3):
            try:
                result = handler.generate_music(
                    captions=captions,
                    lyrics=lyrics,
                    vocal_language="zh",
                    audio_duration=params["audio_duration"],
                    inference_steps=8,
                    guidance_scale=1.0,
                    use_random_seed=True,
                    seed=-1,
                    task_type="text2music",
                    use_tiled_decode=params["use_tiled_decode"],
                )
                break
            except OSError as oe:
                if gen_retry < 2:
                    print(f"[acestep] Generate retry {gen_retry+1}/3: {oe}", file=sys.stderr)
                    time.sleep(3)
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                else:
                    raise

        # 提取音频
        audio_data = None
        sample_rate = 48000

        if isinstance(result, dict):
            if "audios" in result and result["audios"]:
                audios = result["audios"]
                if audios:
                    first = audios[0]
                    if isinstance(first, dict):
                        audio_data = first.get("tensor")
                        sample_rate = first.get("sample_rate", 48000)
                    elif hasattr(first, "tensor"):
                        audio_data = first.tensor
                        sample_rate = getattr(first, "sample_rate", 48000)
            elif "audio_data" in result:
                audio_data = result["audio_data"]
            elif "audio" in result:
                audio_data = result["audio"]

        if audio_data is not None:
            if isinstance(audio_data, torch.Tensor):
                arr = audio_data.cpu().numpy()
                if arr.ndim == 2:
                    arr = arr.T
                audio_data = arr

            sf.write(output_path, audio_data, sample_rate)
            info = sf.info(output_path)
            duration_actual = info.frames / info.samplerate

            print(f"[acestep] OK: {duration_actual:.1f}s", file=sys.stderr)
            return output_path, duration_actual

        print(f"[acestep] Attempt {i+1} failed, retrying...", file=sys.stderr)

    return None, 0


def main():
    parser = argparse.ArgumentParser(description="ACE-Step BGM CLI")
    parser.add_argument("--lyrics", required=True, help="歌词文件路径")
    parser.add_argument("--output", required=True, help="输出WAV文件路径")
    parser.add_argument("--duration", type=float, default=120, help="目标时长(秒)")
    parser.add_argument("--captions", default="electronic, tech, cinematic, 100 BPM, suspenseful to inspirational",
                        help="音乐风格描述")
    args = parser.parse_args()

    # 读取歌词
    with open(args.lyrics, "r", encoding="utf-8") as f:
        lyrics = f.read().strip()

    if not lyrics:
        print(json.dumps({"error": "歌词为空"}))
        sys.exit(1)

    # 输出目录
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    # 初始化
    handler = init_handler()

    # 生成
    path, dur = generate_bgm(handler, lyrics, args.output, args.duration, args.captions)

    if path:
        print(json.dumps({
            "success": True,
            "path": path,
            "duration": round(dur, 2),
        }))
    else:
        print(json.dumps({"error": "BGM生成失败"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
