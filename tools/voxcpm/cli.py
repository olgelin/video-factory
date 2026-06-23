#!/usr/bin/env python3
"""
VoxCPM2 TTS 工具 - 独立CLI接口
用法:
  python cli.py --input script.json --output voice.wav [--speed 1.2] [--ref-audio ref.wav] [--cfg 2.0] [--steps 10]

输入格式 (JSON):
  {"sections": [{"text": "..."}, {"text": "..."}]}
  或
  {"voiceover_sections": [{"content": "..."}, ...]}
  或
  {"text": "直接文本"}

输出:
  生成的WAV文件 + stdout输出JSON元数据
"""

import argparse
import json
import os
import sys
import shutil
import subprocess
from pathlib import Path

# === 环境隔离：只移除hermes-agent/venv的路径，不影响tools/下的venv ===
if 'PYTHONPATH' in os.environ:
    del os.environ['PYTHONPATH']
sys.path[:] = [p for p in sys.path if not any(
    x in p.lower() for x in ['hermes-agent\\venv', 'hermes_agent\\venv', 'hermes-agent/venv', 'hermes_agent/venv']
)]
sys.meta_path = [f for f in sys.meta_path if 'hermes' not in type(f).__module__.lower() and 'hermes' not in type(f).__name__.lower()]

import numpy as np
import soundfile as sf

# 模型路径
VOXCPM_MODEL = os.environ.get(
    "VOXCPM_MODEL",
    "E:/Hermes-Agent/workspace/xiaoshan/models/models--openbmb--VoxCPM2/snapshots/bffb3df5a29440629464e5e839f4d214c8714c3d"
)

# 参考音频
DEFAULT_REF_WAV = os.environ.get(
    "VOICE_REF_WAV",
    "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/assets/reference_voice.wav"
)

# text_preprocessor路径
TOOLS_DIR = Path(__file__).parent.parent
VF_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(VF_ROOT / "hf-project"))
try:
    from text_preprocessor import preprocess_text_for_tts
except ImportError:
    def preprocess_text_for_tts(text):
        return text


def load_model():
    """加载VoxCPM2模型"""
    import torch._dynamo
    torch._dynamo.config.suppress_errors = True
    torch._dynamo.config.disable = True

    from voxcpm import VoxCPM
    print("[voxcpm] Loading model...", file=sys.stderr)
    model = VoxCPM.from_pretrained(VOXCPM_MODEL, load_denoiser=False)
    print(f"[voxcpm] Model loaded on {model.tts_model.device}", file=sys.stderr)
    return model


def generate_single(model, text, output_path, ref_wav, cfg=2.0, steps=10):
    """生成单段配音"""
    import torch

    text = preprocess_text_for_tts(text)
    prompt_text = "大家好 今天给大家拆解一套AI视频生成方案核心逻辑就是用双AZ的架构实现从文本到成片权"

    max_retries = 3
    wav = None
    for attempt in range(max_retries):
        try:
            wav = model.generate(
                text=text,
                reference_wav_path=ref_wav,
                prompt_wav_path=ref_wav,
                prompt_text=prompt_text,
                cfg_value=cfg,
                inference_timesteps=steps,
            )
            break
        except Exception as e:
            print(f"[voxcpm] Retry {attempt+1}/{max_retries}: {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                continue
            raise

    orig_sr = model.tts_model.sample_rate
    duration = wav.shape[0] / orig_sr

    # 淡入防爆音
    fade_samples = int(0.1 * orig_sr)
    if len(wav) > fade_samples:
        fade = np.linspace(0, 1, fade_samples)
        wav[:fade_samples] *= fade

    sf.write(output_path, wav, orig_sr)

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return output_path, duration


def apply_speed(input_path, output_path, speed=1.15):
    """FFmpeg加速"""
    if speed == 1.0:
        data, sr = sf.read(input_path)
        return input_path, len(data) / sr

    result = subprocess.run(
        ['ffmpeg', '-y', '-i', input_path,
         '-filter_complex', f'atempo={speed}',
         '-q:a', '0', output_path],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        data, sr = sf.read(input_path)
        return input_path, len(data) / sr

    data, sr = sf.read(output_path)
    return output_path, len(data) / sr


def extract_sections(input_data):
    """从输入数据提取文本段落"""
    if isinstance(input_data, str):
        return [{"text": input_data}]

    sections = []

    # 格式1: {"sections": [{"text": "..."}]}
    if "sections" in input_data:
        for s in input_data["sections"]:
            text = s.get("text", "") or s.get("content", "")
            if text:
                sections.append({"text": text})

    # 格式2: {"voiceover_sections": [{"content": "..."}]}
    elif "voiceover_sections" in input_data:
        for s in input_data["voiceover_sections"]:
            text = s.get("content", "") or s.get("voiceover", "") or s.get("text", "")
            if text:
                sections.append({"text": text})

    # 格式3: {"text": "..."}
    elif "text" in input_data:
        sections.append({"text": input_data["text"]})

    return sections


def main():
    parser = argparse.ArgumentParser(description="VoxCPM2 TTS CLI")
    parser.add_argument("--input", required=True, help="输入JSON文件或直接文本")
    parser.add_argument("--output", required=True, help="输出WAV文件路径")
    parser.add_argument("--speed", type=float, default=1.0, help="语速倍率")
    parser.add_argument("--ref-audio", default=DEFAULT_REF_WAV, help="参考音频路径")
    parser.add_argument("--cfg", type=float, default=2.0, help="CFG值")
    parser.add_argument("--steps", type=int, default=10, help="推理步数")
    args = parser.parse_args()

    # 读取输入
    if os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            input_data = json.load(f)
    else:
        input_data = {"text": args.input}

    sections = extract_sections(input_data)
    if not sections:
        print(json.dumps({"error": "没有找到文本段落"}))
        sys.exit(1)

    # 加载模型
    model = load_model()

    # 输出目录
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 逐段生成
    voice_files = []
    total_duration = 0.0

    for i, section in enumerate(sections):
        text = section["text"]
        scene_path = str(output_dir / f"_voxcpm_scene{i:02d}.wav")
        print(f"[voxcpm] Section {i+1}/{len(sections)}: {text[:40]}...", file=sys.stderr)

        try:
            p, dur = generate_single(model, text, scene_path, args.ref_audio, args.cfg, args.steps)
            voice_files.append({"file": p, "duration": dur})
            total_duration += dur
            print(f"[voxcpm]   OK {dur:.1f}s", file=sys.stderr)
        except Exception as e:
            print(f"[voxcpm]   FAIL: {e}", file=sys.stderr)

    if not voice_files:
        print(json.dumps({"error": "所有段落生成失败"}))
        sys.exit(1)

    # 加速
    if args.speed != 1.0:
        for vf in voice_files:
            speed_path = vf["file"].replace(".wav", "_speed.wav")
            result, actual_dur = apply_speed(vf["file"], speed_path, args.speed)
            if result != vf["file"]:
                os.unlink(vf["file"])
                os.rename(speed_path, vf["file"])
                vf["duration"] = actual_dur

    # 合并
    if len(voice_files) > 1:
        parts = []
        for vf in voice_files:
            data, sr = sf.read(vf["file"])
            parts.append(data)
        combined = np.concatenate(parts)
        sf.write(args.output, combined, sr)
        total_duration = sum(vf["duration"] for vf in voice_files)
    else:
        shutil.copy(voice_files[0]["file"], args.output)
        total_duration = voice_files[0]["duration"]

    # 清理临时文件
    for vf in voice_files:
        try:
            os.unlink(vf["file"])
        except Exception:
            pass

    # 输出元数据到stdout
    scene_durations = [round(vf["duration"], 2) for vf in voice_files]
    result = {
        "success": True,
        "path": args.output,
        "duration": round(total_duration, 2),
        "sections": len(sections),
        "scene_durations": scene_durations,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
