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

# LLM 生成提示词的 system prompt（批量：一次生成所有场景）
_PROMPT_SYSTEM = """你是 Vox 风格解释视频的氛围底图提示词专家。
给每个场景生成一句英文 ComfyUI(SDXL) 提示词，用于生成科技风氛围背景图。

铁律：
1. 只描述"氛围/光效/纹理/粒子"等抽象背景，不描述具体物体主体（主体由 HTML 内容承担）
2. 保持科技风基调：dark + 霓虹青蓝 cyan/blue/purple，或贴合场景情绪的色调
3. 结尾固定加 ", abstract background, cinematic, high detail, no text"
4. 每句 15-30 个英文单词，简洁
5. 输出 JSON 数组：[{"scene_id": 1, "prompt": "..."}, ...]

只输出 JSON，不要任何解释。"""


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

    # 3. LLM 批量生成英文提示词
    prompts = _generate_prompts(scenes)

    # 4. 逐个调 ComfyUI 出图
    atmosphere_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    for scene in scenes:
        sid = scene.get("scene_id", 1)
        prompt = prompts.get(sid) or _fallback_prompt(scene)
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
    return context


# ── 内部函数 ──

def _comfy_available() -> bool:
    """探测 ComfyUI 服务是否在运行"""
    try:
        req = urllib.request.Request(f"{COMFY_URL}/system_stats")
        urllib.request.urlopen(req, timeout=COMFY_TIMEOUT)
        return True
    except Exception:
        return False


def _load_scenes(sb_path: str) -> list:
    with open(sb_path, encoding="utf-8") as f:
        sb = json.load(f)
    if isinstance(sb, list):
        return sb
    return sb.get("scenes", [])


def _generate_prompts(scenes: list) -> dict:
    """LLM 批量生成每个场景的英文提示词。失败则返回空 dict（走 fallback）。"""
    try:
        from llm_utils import call_llm
        scene_info = [
            {
                "scene_id": s.get("scene_id", i + 1),
                "concept": str(s.get("concept", ""))[:120],
                "mood": str(s.get("mood", ""))[:80],
            }
            for i, s in enumerate(scenes)
        ]
        user_prompt = "场景列表：\n" + json.dumps(scene_info, ensure_ascii=False, indent=2)
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


def _fallback_prompt(scene: dict) -> str:
    """无 LLM 时的固定科技风提示词兜底"""
    mood = str(scene.get("mood", "")).lower()
    base = "dark blue purple tech atmosphere, glowing cyan neon lines, particle stars, futuristic"
    if any(w in mood for w in ["海", "ocean", "水", "wave", "深"]):
        base = "deep dark blue ocean atmosphere, subtle underwater light rays, floating particles, mysterious deep sea glow"
    elif any(w in mood for w in ["数据", "data", "科技", "tech"]):
        base = "dark blue purple data visualization atmosphere, glowing cyan grid lines, rising data streams, futuristic analytics"
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
