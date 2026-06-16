"""
voice_gen/impl.py — VoxCPM2配音生成 v2
功能：逐段落生成配音，然后合并

关键改进（相比v1）：
1. 逐段落生成，不是合并成一大段
2. 使用text_preprocessor处理数字
3. 使用FFmpeg atempo调整速度（1.15x）
4. 使用soundfile保存音频

输入：step03_script.json
输出：step05_voice.wav

参考原版step05_voice的实现。
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from text_preprocessor import preprocess_text_for_tts

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
VOICE_PATH = OUTPUT_DIR / "step05_voice.wav"

# 参考音频
DEFAULT_REF_WAV = os.environ.get("VOICE_REF_WAV", "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/assets/reference_voice.wav")

# VoxCPM2模型路径
VOXCPM_MODEL = os.environ.get("VOXCPM_MODEL", "E:/Hermes-Agent/workspace/xiaoshan/models/models--openbmb--VoxCPM2/snapshots/bffb3df5a29440629464e5e839f4d214c8714c3d")

# 全局模型缓存
MODEL = None


def load_model():
    """加载VoxCPM2模型"""
    global MODEL
    if MODEL is None:
        import torch._dynamo
        torch._dynamo.config.suppress_errors = True
        torch._dynamo.config.disable = True

        from voxcpm import VoxCPM
        print(f"  [voice-gen] Loading VoxCPM2...")
        MODEL = VoxCPM.from_pretrained(VOXCPM_MODEL, load_denoiser=False)
        print(f"  [voice-gen] Model loaded on {MODEL.tts_model.device}")
    return MODEL


def generate_single(text: str, output_path: str, ref_wav: str, cfg: float = 2.0, steps: int = 15) -> tuple:
    """生成单个段落的配音"""
    model = load_model()

    # 预处理文本（数字→中文）
    text = preprocess_text_for_tts(text)
    print(f"    Text: {text[:50]}...")

    # 生成（带重试+GPU缓存清理）
    import torch
    max_retries = 3
    wav = None
    for attempt in range(max_retries):
        try:
            wav = model.generate(
                text=text,
                reference_wav_path=ref_wav,
                cfg_value=cfg,
                inference_timesteps=steps,
            )
            break
        except Exception as e:
            print(f"    ⚠️ 生成失败 (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                continue
            raise

    # 获取采样率
    orig_sr = model.tts_model.sample_rate
    duration = wav.shape[0] / orig_sr

    # 淡入防爆音（100ms）
    fade_samples = int(0.1 * orig_sr)
    if len(wav) > fade_samples:
        fade = np.linspace(0, 1, fade_samples)
        wav[:fade_samples] *= fade

    # 保存
    sf.write(output_path, wav, orig_sr)

    # 清理GPU缓存
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return output_path, duration


def apply_speed(input_path: str, output_path: str, speed: float = 1.15) -> float:
    """使用FFmpeg atempo调整速度"""
    if speed == 1.0:
        return input_path

    result = subprocess.run([
        'ffmpeg', '-y', '-i', input_path,
        '-filter_complex', f'atempo={speed}',
        '-q:a', '0', output_path
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  [voice-gen] FFmpeg atempo failed: {result.stderr[-200:]}")
        return input_path

    # 获取新时长
    data, sr = sf.read(output_path)
    duration = len(data) / sr
    return output_path, duration


def run(context: dict) -> dict:
    """主入口：逐段落生成配音"""

    # 读取脚本
    script_path = context.get("script_path") or str(OUTPUT_DIR / "step03_script.json")
    if not os.path.exists(script_path):
        print(f"  ❌ [voice-gen] 找不到脚本: {script_path}")
        return context

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    # 读取段落（兼容新旧格式）
    sections = script_data.get("voiceover_sections", [])
    if not sections:
        sections = script_data.get("scenes", [])

    if not sections:
        print(f"  ❌ [voice-gen] 脚本中没有段落")
        return context

    print(f"  [voice-gen] 共 {len(sections)} 个段落")

    # 参考音频
    ref_wav = context.get("voice_ref") or DEFAULT_REF_WAV
    if not os.path.exists(ref_wav):
        print(f"  ⚠️ [voice-gen] 参考音频不存在: {ref_wav}，使用默认")
        ref_wav = DEFAULT_REF_WAV

    # 参数
    cfg = context.get("voice_cfg", 2.0)
    steps = context.get("voice_steps", 15)
    speed = context.get("voice_speed", 1.2)

    print(f"  [voice-gen] 参考音频: {ref_wav}")
    print(f"  [voice-gen] 参数: cfg={cfg}, steps={steps}, speed={speed}x")

    # 删除旧文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if VOICE_PATH.exists():
        print(f"  [voice-gen] 删除旧文件: {VOICE_PATH.name}")
        VOICE_PATH.unlink()

    # 逐段落生成
    voice_files = []
    total_duration = 0.0

    for i, section in enumerate(sections):
        text = section.get("content", "") or section.get("voiceover", "") or section.get("text", "")
        if not text:
            continue

        scene_path = str(OUTPUT_DIR / f"step05_voice_scene{i:02d}.wav")
        print(f"  [voice-gen] 段落 {i+1}/{len(sections)}:")

        try:
            p, dur = generate_single(text, scene_path, ref_wav, cfg, steps)
            voice_files.append({"file": p, "text": text, "duration": dur})
            total_duration += dur
            print(f"    ✅ {dur:.1f}s")
        except Exception as e:
            print(f"    ❌ 失败: {e}")
            continue

    if not voice_files:
        print(f"  ❌ [voice-gen] 所有段落生成失败")
        return context

    # 合并所有段落
    if len(voice_files) > 1:
        print(f"  [voice-gen] 合并 {len(voice_files)} 个段落...")
        parts = []
        for vf in voice_files:
            data, sr = sf.read(vf["file"])
            parts.append(data)
        combined = np.concatenate(parts)
        sf.write(str(VOICE_PATH), combined, sr)
        print(f"  [voice-gen] 合并完成: {total_duration:.1f}s")
    else:
        shutil.copy(voice_files[0]["file"], str(VOICE_PATH))

    # 应用速度调整
    if speed != 1.0:
        print(f"  [voice-gen] 应用速度调整: {speed}x")
        tmp_path = str(VOICE_PATH) + ".tmp.wav"
        result, new_dur = apply_speed(str(VOICE_PATH), tmp_path, speed)
        if result != str(VOICE_PATH):
            os.unlink(str(VOICE_PATH))
            os.rename(tmp_path, str(VOICE_PATH))
            total_duration = new_dur
            print(f"  [voice-gen] 速度调整后: {new_dur:.1f}s")
        else:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # 保存每个场景的配音时长（加速后）
    scene_durations = []
    for vf in voice_files:
        adjusted_dur = round(vf["duration"] / speed, 2) if speed > 0 else round(vf["duration"], 2)
        scene_durations.append({"text": vf["text"][:30], "duration": adjusted_dur})
    context["voice_scene_durations"] = scene_durations
    dur_strs = [f"{d['duration']}s" for d in scene_durations]
    print(f"  [voice-gen] 各场景时长: {dur_strs}")

    # 清理临时文件
    for vf in voice_files:
        try:
            os.unlink(vf["file"])
        except:
            pass

    print(f"  [voice-gen] ✅ 配音生成完成: {total_duration:.1f}s -> {VOICE_PATH}")

    # 更新context
    context["voice_path"] = str(VOICE_PATH)
    context["voice_duration"] = total_duration

    return context


if __name__ == "__main__":
    test_context = {
        "script_path": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/output/step03_script.json",
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  配音路径: {result.get('voice_path')}")
    print(f"  时长: {result.get('voice_duration')}")
