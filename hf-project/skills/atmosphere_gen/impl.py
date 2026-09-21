"""
atmosphere_gen/impl.py — VOX 氛围图生成器

读 storyboard，对每个场景用 LLM 生成英文 ComfyUI 提示词，调 ComfyUI 出科技风氛围底图。

职责边界：
- 只负责氛围底图（背景层），不负责场景内容（那是 hf_builder 的事）
- 只在 vox 管线被调用（其他管线 yaml 不引用此 skill）
- ComfyUI 服务不可用时降级兜底（跳过不报错，hf_builder 回退纯 CSS 背景）

输入：output/storyboard.json
输出：output/atmosphere/beat-{scene_id}.png
"""

import json
import os
import time
import uuid
import urllib.request
from pathlib import Path

COMFY_URL = "http://127.0.0.1:8188"
COMFY_TIMEOUT = 3  # 服务探测超时（秒）

# SDXL 文生图 workflow（16:9 画幅，API 格式，无 _comment 字段）
SDXL_WORKFLOW = {
    "3": {
        "class_type": "KSampler",
        "inputs": {"seed": 0, "steps": 24, "cfg": 7.0,
                   "sampler_name": "euler", "scheduler": "normal",
                   "denoise": 1.0, "model": ["4", 0],
                   "positive": ["6", 0], "negative": ["7", 0],
                   "latent_image": ["5", 0]},
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": 1024, "height": 576, "batch_size": 1},
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "", "clip": ["4", 1]},
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "text, words, letters, watermark, logo, signature, low quality, blurry", "clip": ["4", 1]},
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "atmo", "images": ["8", 0]},
    },
}

# Flux fp8 文生图 workflow（16:9 画幅，质量更高，需 4 个模型文件）
FLUX_WORKFLOW = {
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["11", 0]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["10", 0]}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "atmo", "images": ["8", 0]}},
    "10": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
    "11": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn.safetensors", "clip_name2": "clip_l.safetensors", "type": "flux"}},
    "12": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-dev-fp8.safetensors", "weight_dtype": "default"}},
    "13": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["25", 0], "guider": ["22", 0], "sampler": ["16", 0], "sigmas": ["17", 0], "latent_image": ["27", 0]}},
    "16": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
    "17": {"class_type": "BasicScheduler", "inputs": {"scheduler": "simple", "steps": 20, "denoise": 1.0, "model": ["12", 0]}},
    "22": {"class_type": "BasicGuider", "inputs": {"model": ["12", 0], "conditioning": ["6", 0]}},
    "25": {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}},
    "27": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1024, "height": 576, "batch_size": 1}},
}

# Krea-2 Turbo 文生图 workflow（16:9 画幅，8步出图，审美好，可商用<100万美元营收）
# 结构：UNETLoader + CLIPLoader(Qwen3-VL) + VAELoader + KSampler(8步/CFG1.0)
KREA2_WORKFLOW = {
    "3": {"class_type": "KSampler", "inputs": {"seed": 0, "steps": 8, "cfg": 1.0,
            "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0,
            "model": ["10", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0]}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 576, "batch_size": 1}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["11", 0]}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["11", 0]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["12", 0]}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "atmo", "images": ["8", 0]}},
    "10": {"class_type": "UNETLoader", "inputs": {"unet_name": "krea2_turbo_fp8_scaled.safetensors", "weight_dtype": "default"}},
    "11": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_4b_fp8_scaled.safetensors", "type": "krea2"}},
    "12": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
}

# ComfyUI 模型目录（unet 可能在 checkpoints 或 diffusion_models）
_COMFY_MODELS = Path("E:/comfyui/models")

# LLM 生成提示词的 system prompt（从 prompts/atmosphere_system.md 读取，不硬编码）
def _load_prompt_system() -> str:
    prompt_file = Path(__file__).parent / "prompts" / "atmosphere_system.md"
    try:
        return prompt_file.read_text(encoding="utf-8")
    except Exception:
        # 兜底（.md 缺失时）
        return "你是科技风氛围底图提示词专家。给每个场景生成英文 ComfyUI 提示词，暗色抽象背景，无文字无主体，结尾加 ', abstract background, cinematic, high detail, no text'。输出 JSON 数组。"


_PROMPT_SYSTEM = _load_prompt_system()


def run(context: dict) -> dict:
    project_root = Path(context.get("project_root", Path(__file__).parent.parent.parent))
    output_dir = project_root / "output"
    atmosphere_dir = output_dir / "atmosphere"

    # 1. 检查 ComfyUI 服务可用性（降级兜底）
    if not _comfy_available():
        print("  [atmosphere-gen] ⚠️ ComfyUI 服务不可用，跳过氛围图（降级兜底：hf_builder 回退纯 CSS 背景）")
        context["atmosphere_available"] = False
        return context

    # 2. 读 storyboard
    sb_path = context.get("storyboard_path") or str(output_dir / "storyboard.json")
    if not os.path.exists(sb_path):
        print("  [atmosphere-gen] ⚠️ storyboard.json 不存在，跳过")
        context["atmosphere_available"] = False
        return context
    scenes = _load_scenes(sb_path)
    if not scenes:
        print("  [atmosphere-gen] ⚠️ storyboard 无场景，跳过")
        context["atmosphere_available"] = False
        return context

    print(f"  [atmosphere-gen] 为 {len(scenes)} 个场景生成氛围图...")

    # 清空本目录旧氛围图（氛围图是"本视频专属"，不同话题必须重新出图，防止复用旧图串味）
    atmosphere_dir.mkdir(parents=True, exist_ok=True)
    _cleaned = 0
    for old in atmosphere_dir.glob("beat-*.png"):
        old.unlink()
        _cleaned += 1
    if _cleaned:
        print(f"  [atmosphere-gen] 清理旧氛围图 ×{_cleaned}")

    # 3. LLM 批量生成英文提示词（传入 video_style，让背景图匹配视频类型基调）
    video_style = str(context.get("video_style", "news"))
    prompts = _generate_prompts(scenes, video_style)

    # 4. 逐个调 ComfyUI 出图
    atmosphere_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    for scene in scenes:
        sid = scene.get("scene_id", 1)
        prompt = prompts.get(sid) or _fallback_prompt(scene, video_style)
        img_path = atmosphere_dir / f"beat-{sid}.png"
        if img_path.exists():
            generated += 1
            continue  # 已生成，跳过
        ok = _generate_image(prompt, str(img_path))
        if ok:
            generated += 1
            print(f"  [atmosphere-gen] ✅ beat-{sid}.png")
        else:
            print(f"  [atmosphere-gen] ⚠️ beat-{sid}.png 生成失败")
        time.sleep(0.5)  # 微间隔

    context["atmosphere_available"] = generated > 0
    context["atmosphere_dir"] = str(atmosphere_dir)
    context["atmosphere_count"] = generated
    print(f"  [atmosphere-gen] 完成：{generated}/{len(scenes)} 张氛围图")

    # 生图完成后释放 ComfyUI 显存（否则模型缓存占 5-6GB，挤占后续 voxcpm/其他环节显存）
    _free_comfy_vram()
    return context


# ── 内部函数 ──

def _comfy_available() -> bool:
    """探测 ComfyUI 服务是否在运行；掉线则自动拉起并等待启动（自愈）"""
    if _ping_comfy():
        return True
    # 掉线 → 自动拉起
    print("  [atmosphere-gen] ⚠️ ComfyUI 服务未运行，自动拉起...")
    _start_comfy()
    # 等待启动（最多 90 秒，每 5 秒探测一次）
    for _ in range(18):
        time.sleep(5)
        if _ping_comfy():
            print("  [atmosphere-gen] ✅ ComfyUI 已拉起")
            return True
    print("  [atmosphere-gen] ❌ ComfyUI 拉起失败，降级兜底")
    return False


def _ping_comfy() -> bool:
    """单次探测 ComfyUI 是否在线"""
    try:
        req = urllib.request.Request(f"{COMFY_URL}/system_stats")
        urllib.request.urlopen(req, timeout=COMFY_TIMEOUT)
        return True
    except Exception:
        return False


def _start_comfy():
    """后台拉起 ComfyUI 服务（不阻塞）"""
    import subprocess
    try:
        subprocess.Popen(
            ["comfy", "--skip-prompt", "--workspace", "E:/comfyui", "launch", "--background"],
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd="E:/comfyui",
        )
    except Exception as e:
        print(f"  [atmosphere-gen] ⚠️ 拉起 ComfyUI 失败: {e}")


def _free_comfy_vram():
    """生图完成后释放 ComfyUI 缓存的模型显存（/free 端点），避免挤占后续环节显存"""
    try:
        req = urllib.request.Request(
            f"{COMFY_URL}/free",
            data=json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        print("  [atmosphere-gen] ♻️ 已释放 ComfyUI 显存")
    except Exception as e:
        print(f"  [atmosphere-gen] ⚠️ 释放 ComfyUI 显存失败: {e}")


def _load_scenes(sb_path: str) -> list:
    with open(sb_path, encoding="utf-8") as f:
        sb = json.load(f)
    if isinstance(sb, list):
        return sb
    return sb.get("scenes", [])


def _generate_prompts(scenes: list, video_style: str = "news") -> dict:
    """LLM 批量生成每个场景的英文提示词。失败则返回空 dict（走 fallback）。"""
    try:
        from llm_utils import call_llm
        scene_info = [
            {
                "scene_id": s.get("scene_id", i + 1),
                "visual_type": str(s.get("visual_type", "")),
                "concept": str(s.get("concept", ""))[:120],
                "mood": str(s.get("mood", ""))[:80],
            }
            for i, s in enumerate(scenes)
        ]
        user_prompt = f"video_style: {video_style}\n场景列表：\n" + json.dumps(scene_info, ensure_ascii=False, indent=2)
        resp = call_llm(user_prompt, _PROMPT_SYSTEM, max_tokens=2000)
        # 剥 markdown 代码块
        resp = resp.strip()
        if resp.startswith("```"):
            resp = resp.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = json.loads(resp)
        return {item["scene_id"]: item["prompt"] for item in data if "prompt" in item}
    except Exception as e:
        print(f"  [atmosphere-gen] ⚠️ LLM 提示词生成失败({e})，全部走 fallback")
        return {}


def _fallback_prompt(scene: dict, video_style: str = "news") -> str:
    """无 LLM 时的固定提示词兜底（按 video_style 决定基调 + visual_type 微调构图）"""
    vt = str(scene.get("visual_type", "")).lower()
    # 按 video_style 决定基调（不是统一科技风）
    base_map = {
        "news": "dark blue purple tech atmosphere, glowing cyan neon lines, particle stars, futuristic",
        "edu": "soft warm learning atmosphere, light blue and cream tones, gentle glow, paper texture, no neon",
        "edu_music": "soft educational atmosphere, musical notes and sound wave motifs, gentle pastel tones",
        "vox": "clean minimal atmosphere, restrained blue purple, geometric shapes, lots of negative space",
    }
    base = base_map.get(video_style, base_map["news"])
    # 按 visual_type 微调构图（确定性映射，非词表）
    vt_style = {
        "quote_hero": "minimal backdrop, soft radial glow, empty center for large text",
        "data_impact": "rising data streams, glowing grid lines, analytics atmosphere",
        "compare": "split lighting left and right, dual tone atmosphere",
        "flow": "flowing light trails, directional particle stream",
        "list_alert": "dark ominous atmosphere, warning glow accents",
        "timeline_event": "horizontal light band, side-scrolling glow",
        "hud": "grid overlay, scan lines, corner frame glow",
    }.get(vt, "")
    if vt_style:
        base = f"{base}, {vt_style}"
    return f"{base}, abstract background, cinematic, high detail, no text"


def _krea2_ready() -> bool:
    """检测 Krea-2 Turbo 的 3 个模型文件是否全部就绪"""
    unet = (_COMFY_MODELS / "diffusion_models" / "krea2_turbo_fp8_scaled.safetensors").exists()
    clip = (_COMFY_MODELS / "text_encoders" / "qwen3vl_4b_fp8_scaled.safetensors").exists()
    vae = (_COMFY_MODELS / "vae" / "qwen_image_vae.safetensors").exists()
    return all([unet, clip, vae])


def _flux_ready() -> bool:
    """检测 Flux 的 4 个模型文件是否全部就绪"""
    unet = (_COMFY_MODELS / "checkpoints" / "flux1-dev-fp8.safetensors").exists() or \
           (_COMFY_MODELS / "diffusion_models" / "flux1-dev-fp8.safetensors").exists()
    clip_l = (_COMFY_MODELS / "text_encoders" / "clip_l.safetensors").exists()
    t5xxl = (_COMFY_MODELS / "text_encoders" / "t5xxl_fp8_e4m3fn.safetensors").exists()
    vae = (_COMFY_MODELS / "vae" / "ae.safetensors").exists()
    return all([unet, clip_l, t5xxl, vae])


def _select_workflow() -> tuple:
    """选择出图模型（优先级：Krea-2 > Flux > SDXL）。返回 (workflow, seed_key)"""
    if _krea2_ready():
        return KREA2_WORKFLOW, "3"   # Krea-2 的种子在节点 3（KSampler）
    if _flux_ready():
        return FLUX_WORKFLOW, "25"   # Flux 的噪声种子在节点 25
    return SDXL_WORKFLOW, "3"        # SDXL 的种子在节点 3


def _generate_image(prompt: str, save_path: str) -> bool:
    """调 ComfyUI 出图并保存到 save_path"""
    wf, seed_key = _select_workflow()
    wf = json.loads(json.dumps(wf))  # deep copy
    wf["6"]["inputs"]["text"] = prompt
    wf[seed_key]["inputs"]["seed" if seed_key == "3" else "noise_seed"] = uuid.uuid4().int % 100000
    try:
        payload = {"prompt": wf, "client_id": str(uuid.uuid4())}
        req = urllib.request.Request(
            f"{COMFY_URL}/prompt",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        r = json.loads(resp.read().decode())
        prompt_id = r.get("prompt_id")
        if not prompt_id:
            return False
        # 轮询等待生成完成
        return _wait_and_fetch(prompt_id, save_path, timeout=300 if _flux_ready() else 180)
    except Exception as e:
        print(f"  [atmosphere-gen] ComfyUI 调用失败: {e}")
        return False


def _wait_and_fetch(prompt_id: str, save_path: str, timeout: int = 180) -> bool:
    """轮询 history 直到生成完成，下载输出到 save_path"""
    import shutil
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            entry = data.get(prompt_id, {})
            status = entry.get("status", {}).get("status_str", "")
            if status == "success":
                outputs = entry.get("outputs", {})
                for node_outputs in outputs.values():
                    for img in node_outputs.get("images", []):
                        filename = img.get("filename")
                        subfolder = img.get("subfolder", "")
                        ftype = img.get("type", "output")
                        # 下载
                        url = f"{COMFY_URL}/view?filename={filename}&subfolder={subfolder}&type={ftype}"
                        r2 = urllib.request.urlopen(urllib.request.Request(url), timeout=30)
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        with open(save_path, "wb") as f:
                            f.write(r2.read())
                        return True
                return False
            elif status in ("error", "failed"):
                return False
        except Exception:
            pass
        time.sleep(2)
    return False
