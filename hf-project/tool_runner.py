#!/usr/bin/env python3
"""
工具调用器 - 统一的subprocess接口
所有ML工具通过此模块调用，与pipeline主环境完全隔离
"""

import subprocess
import json
import os
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent.parent / "tools"


def call_tool(tool_name: str, cli_args: list, timeout: int = 600) -> dict:
    """
    调用工具的CLI接口

    Args:
        tool_name: 工具名 (voxcpm, acestep, transcriber)
        cli_args: CLI参数列表
        timeout: 超时秒数

    Returns:
        dict: 工具输出的JSON元数据
    """
    tool_dir = TOOLS_DIR / tool_name
    venv_python = tool_dir / ".venv" / "Scripts" / "python.exe"
    cli_script = tool_dir / "cli.py"

    if not venv_python.exists():
        raise FileNotFoundError(f"工具venv不存在: {venv_python}")
    if not cli_script.exists():
        raise FileNotFoundError(f"工具CLI不存在: {cli_script}")

    cmd = [str(venv_python), str(cli_script)] + cli_args

    print(f"  [tool-runner] 调用 {tool_name}: {' '.join(cli_args[:6])}...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(TOOLS_DIR.parent),  # video-factory根目录
            env={**os.environ, 'PYTHONPATH': ''},  # 清除主环境PYTHONPATH，避免site-packages污染
        )

        if result.returncode != 0:
            print(f"  ❌ [tool-runner] {tool_name} 失败 (exit={result.returncode})")
            if result.stderr:
                print(f"     stderr: {result.stderr[-300:]}")
            return {"error": f"{tool_name} failed", "stderr": result.stderr[-500:]}

        # 解析stdout中的JSON
        stdout = result.stdout.strip()
        if stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                # stdout可能包含非JSON内容（如print语句），尝试找最后一行JSON
                for line in reversed(stdout.split('\n')):
                    line = line.strip()
                    if line.startswith('{'):
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            continue
                return {"error": f"{tool_name} 输出非JSON", "stdout": stdout[-500:]}
        else:
            return {"error": f"{tool_name} 无输出"}

    except subprocess.TimeoutExpired:
        print(f"  ❌ [tool-runner] {tool_name} 超时 ({timeout}s)")
        return {"error": f"{tool_name} timeout"}
    except Exception as e:
        print(f"  ❌ [tool-runner] {tool_name} 异常: {e}")
        return {"error": str(e)}


def call_voxcpm(input_path: str, output_path: str, speed: float = 1.0,
                ref_audio: str = None, cfg: float = 2.0, steps: int = 10) -> dict:
    """调用VoxCPM2 TTS"""
    args = ["--input", input_path, "--output", output_path, "--speed", str(speed),
            "--cfg", str(cfg), "--steps", str(steps)]
    if ref_audio:
        args += ["--ref-audio", ref_audio]
    # 🔴 voxcpm 生成多段配音实际需 10-20 分钟（每段约 45-60s），600s 超时太短
    return call_tool("voxcpm", args, timeout=1800)


def call_acestep(lyrics_path: str, output_path: str, duration: float = 120,
                 captions: str = "electronic, tech, cinematic, 100 BPM") -> dict:
    """调用ACE-Step BGM"""
    args = ["--lyrics", lyrics_path, "--output", output_path,
            "--duration", str(duration), "--captions", captions]
    return call_tool("acestep", args, timeout=600)


def call_transcriber(input_path: str, output_path: str, srt_path: str = None) -> dict:
    """调用Transcriber"""
    args = ["--input", input_path, "--output", output_path]
    if srt_path:
        args += ["--srt-output", srt_path]
    return call_tool("transcriber", args, timeout=300)


# ============================================================
# MiniMax Music3（通过 ComfyUI HTTP API 生成音乐，替换 ACEStep）
# ============================================================
import uuid
import time
import urllib.request

COMFY_URL = "http://127.0.0.1:8188"
MINIMAX_UNET = "minimax_music3_dit_int8_convrot.safetensors"
MINIMAX_CLIP = "minimax_music3_text_encoder_pruned_int8_convrot.safetensors"
MINIMAX_VAE = "minimax_music3_dav.safetensors"


def call_minimax_music3(caption: str, lyrics: str, output_path: str,
                        duration: float = 90, seed: int = None) -> dict:
    """通过 ComfyUI 调用 MiniMax Music3 生成音乐（BGM/完整歌曲）

    caption: 三段式音乐风格描述（Global Metadata / Vocal Details / Arrangement）
    lyrics: 歌词（带结构标签）；纯音乐可为空或 [Instrumental]
    duration: 目标时长上限（秒）。Music3 实际时长由歌词内容密度决定——
              有真实歌词接近目标时长，纯器乐会缩水（这是模型特性）
    """
    import random
    if seed is None:
        seed = random.randint(0, 1000000)

    workflow = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": MINIMAX_UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": MINIMAX_CLIP, "type": "minimax", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": MINIMAX_VAE}},
        "4": {"class_type": "MiniMaxMusic3TextEncode", "inputs": {
            "clip": ["2", 0], "caption": caption, "lyrics": lyrics,
            "seed": seed, "max_duration": float(duration), "cfg_scale": 1.7, "top_k": 50,
        }},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
        "6": {"class_type": "EmptyMiniMaxMusic3LatentAudio", "inputs": {"seconds": ["4", 1], "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "seed": seed, "steps": 30, "cfg": 1.7,
            "sampler_name": "euler", "scheduler": "simple",
            "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "denoise": 1.0,
        }},
        "8": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveAudio", "inputs": {"audio": ["8", 0], "filename_prefix": "bgm_minimax"}},
    }

    try:
        payload = json.dumps({"prompt": workflow, "client_id": str(uuid.uuid4())}).encode("utf-8")
        req = urllib.request.Request(f"{COMFY_URL}/prompt", data=payload,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=60)
        r = json.loads(resp.read().decode())
        prompt_id = r.get("prompt_id")
        if not prompt_id:
            return {"error": f"ComfyUI 提交失败: {json.dumps(r.get('node_errors', {}))[:200]}"}

        # 轮询（Music3 生成时长取决于 max_duration，上限 10 分钟）
        start = time.time()
        timeout = max(600, int(duration * 4))
        while time.time() - start < timeout:
            time.sleep(5)
            try:
                hreq = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
                h = json.loads(urllib.request.urlopen(hreq, timeout=15).read().decode())
            except Exception:
                continue
            entry = h.get(prompt_id, {})
            status = entry.get("status", {}).get("status_str", "")
            if status == "success":
                for node_out in entry.get("outputs", {}).values():
                    for audio in node_out.get("audio", []):
                        filename = audio.get("filename")
                        subfolder = audio.get("subfolder", "")
                        ftype = audio.get("type", "output")
                        url = f"{COMFY_URL}/view?filename={filename}&subfolder={subfolder}&type={ftype}"
                        data = urllib.request.urlopen(urllib.request.Request(url), timeout=120).read()
                        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, "wb") as f:
                            f.write(data)
                        return {"success": True, "path": output_path, "duration": duration, "seed": seed}
                return {"error": "生成成功但无 audio 输出"}
            elif status in ("error", "failed"):
                return {"error": f"ComfyUI 生成失败: {json.dumps(entry.get('status', {}))[:300]}"}
        return {"error": f"ComfyUI 超时 ({timeout}s)"}
    except Exception as e:
        return {"error": f"MiniMax Music3 调用异常: {e}"}
