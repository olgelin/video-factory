"""
qwen_metaphor_gen/impl.py — VOX 视觉隐喻静帧生成器（B-roll）

读 storyboard，提取每个场景的 metaphor（core_metaphor + key_objects），
用 Qwen Image 2.1 把抽象隐喻具象化成一幅写实静帧（16:9），存 output/metaphor/beat-{scene_id}.png。

这是「B-roll 静帧」：隐喻画面作为场景的视觉主体（背景层），HTML 信息卡叠在上面。
- 与 atmosphere_gen（无文字抽象氛围底图）的关系：隐喻图是主力（具象），氛围图降为兜底
- 只在 vox 管线被调用
- ComfyUI 不可用则降级兜底（跳过不报错，hf_builder 回退 atmosphere_gen 氛围图）

输入：output/storyboard.json
输出：output/metaphor/beat-{scene_id}.png
"""

import json
import os
import time
import uuid
import urllib.request
from pathlib import Path

COMFY_URL = "http://127.0.0.1:8188"
COMFY_TIMEOUT = 3

# Qwen Image 2.1 文生图 workflow（16:9，用自定义 EmptyQwenImage21Latent 节点生成非正方形 latent）
QWEN_WORKFLOW = {
    "1": {"class_type": "UNETLoader", "inputs": {
        "unet_name": "qwen_image_2.1_int8_convrot.safetensors", "weight_dtype": "default"}},
    "2": {"class_type": "CLIPLoader", "inputs": {
        "clip_name": "qwen3vl_8b_int8_convrot.safetensors", "type": "qwen_image"}},
    "3": {"class_type": "VAELoader", "inputs": {
        "vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
    "4": {"class_type": "TextEncodeQwenImage21", "inputs": {
        "clip": ["2", 0], "prompt": "", "negative_prompt": "",
        "resolution": 1024, "images": {}, "vae": ["3", 0]}},
    "8": {"class_type": "EmptyQwenImage21Latent", "inputs": {
        "width": 1344, "height": 768, "batch_size": 1}},
    "5": {"class_type": "KSampler", "inputs": {
        "seed": 0, "steps": 25, "cfg": 1.0, "sampler_name": "euler",
        "scheduler": "simple", "denoise": 1.0,
        "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1],
        "latent_image": ["8", 0]}},
    "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["3", 0]}},
    "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "metaphor", "images": ["6", 0]}},
}

# 隐喻静帧 prompt 模板：把抽象隐喻具象化（core_metaphor + key_objects）+ 镜头语言（景别+角度），科技风，无文字
# 无文字是硬约束——隐喻图是背景层，文字由 HTML 信息卡叠上去，图里有文字会跟 HTML 冲突
METAPHOR_PROMPT_TEMPLATE = (
    "An editorial illustration visualizing this metaphor: {core_metaphor}. "
    "The main subject of the image is: {key_objects}. "
    "Camera: {shot_desc} {angle_desc} "
    "Style: clean modern tech editorial, deep blue and purple gradient palette, neon cyan accent lighting, "
    "one strong focal point, cinematic lighting, photographic realism blended with flat graphic design, "
    "high-end magazine quality, lots of negative space around the focal point. "
    "Absolutely no text, no words, no letters, no numbers, no watermark, no logo, "
    "no signage, no shop signs, no storefront names, no banners, no posters, no labels, "
    "no plaques, no lettering, no typography — any storefront/sign/badge should be rendered as "
    "blank, featureless, abstract colored shapes with no writing on them"
)

# 景别 → 英文镜头描述（让生图听导演的景别设计）
SHOT_SIZE_MAP = {
    "closeup": "close-up shot, the main subject fills the frame, focused on detail and emotion",
    "medium": "medium shot, the main subject with some surrounding environment",
    "wide": "wide shot, the main subject small within a vast environment, emphasizing scale",
}

# 角度 → 英文镜头描述（让生图听导演的角度设计）
CAMERA_ANGLE_MAP = {
    "low_angle": "low angle shot looking up, imposing and powerful feel",
    "high_angle": "high angle shot looking down, small and vulnerable feel",
    "eye_level": "eye-level shot, neutral and objective view",
}

# 负面提示词：压制文字/乱码/低质
METAPHOR_NEGATIVE_PROMPT = (
    "text, subtitle, watermark, logo, gibberish, random letters, extra words, "
    "caption, signature, label, numbers, signage, shop sign, storefront sign, brand name, "
    "lettering, typography, poster, banner, plaque, low quality, blurry, multiple subjects, cluttered"
)

_COMFY_MODELS = Path("E:/comfyui/models")


def run(context: dict) -> dict:
    project_root = Path(context.get("project_root", Path(__file__).parent.parent.parent))
    output_dir = project_root / "output"
    metaphor_dir = output_dir / "metaphor"

    # 1. ComfyUI 可用性检查（不可用则降级，不报错）
    if not _comfy_available():
        print("  [qwen-metaphor-gen] ⚠️ ComfyUI 不可用，跳过隐喻图（hf_builder 回退氛围图）")
        context["metaphor_available"] = False
        return context

    # 2. 读 storyboard
    sb_path = context.get("storyboard_path") or str(output_dir / "storyboard.json")
    if not os.path.exists(sb_path):
        print("  [qwen-metaphor-gen] ⚠️ storyboard.json 不存在，跳过")
        context["metaphor_available"] = False
        return context
    scenes = _load_scenes(sb_path)
    if not scenes:
        context["metaphor_available"] = False
        return context

    # 3. 提取所有场景的隐喻（每个场景都有 metaphor 字段）
    metaphor_scenes = _find_metaphor_scenes(scenes)
    if not metaphor_scenes:
        print("  [qwen-metaphor-gen] 无隐喻字段，跳过")
        context["metaphor_available"] = False
        context["metaphor_dir"] = str(metaphor_dir)
        context["metaphor_scenes"] = []
        return context

    # 4. 清空旧隐喻图（本视频专属）
    metaphor_dir.mkdir(parents=True, exist_ok=True)
    for old in metaphor_dir.glob("beat-*.png"):
        old.unlink()

    # 5. 逐个场景生成隐喻静帧
    generated = 0
    for scene in metaphor_scenes:
        sid = scene.get("scene_id", 1)
        core = scene.get("_core_metaphor", "")
        objs = scene.get("_key_objects", [])
        if not core:
            continue
        key_objects = ", ".join(objs) if objs else core
        shot_desc = SHOT_SIZE_MAP.get(scene.get("_shot_size", ""), "")
        angle_desc = CAMERA_ANGLE_MAP.get(scene.get("_camera_angle", ""), "")
        prompt = METAPHOR_PROMPT_TEMPLATE.format(
            core_metaphor=core, key_objects=key_objects,
            shot_desc=shot_desc, angle_desc=angle_desc,
        )
        img_path = metaphor_dir / f"beat-{sid}.png"
        ok = _generate_image(prompt, str(img_path))
        if ok:
            generated += 1
            print(f"  [qwen-metaphor-gen] ✅ beat-{sid}.png「{core[:30]}」")
        else:
            print(f"  [qwen-metaphor-gen] ⚠️ beat-{sid}.png 生成失败")
        time.sleep(0.5)

    context["metaphor_available"] = generated > 0
    context["metaphor_dir"] = str(metaphor_dir)
    context["metaphor_scenes"] = [s.get("scene_id") for s in metaphor_scenes if s.get("_core_metaphor")]
    print(f"  [qwen-metaphor-gen] 完成：{generated}/{len(metaphor_scenes)} 张隐喻静帧")

    _free_comfy_vram()
    return context


# ── 内部函数 ──

def _find_metaphor_scenes(scenes: list) -> list:
    """提取所有场景的 metaphor 字段（core_metaphor + key_objects + shot_size + camera_angle）。"""
    metaphor_scenes = []
    for scene in scenes:
        m = scene.get("metaphor")
        if not isinstance(m, dict):
            continue
        core = str(m.get("core_metaphor", "")).strip()
        objects = m.get("key_objects", [])
        if not core:
            continue
        scene = dict(scene)
        scene["_core_metaphor"] = core
        scene["_key_objects"] = objects if isinstance(objects, list) else []
        scene["_shot_size"] = str(scene.get("shot_size", "")).strip().lower()
        scene["_camera_angle"] = str(scene.get("camera_angle", "")).strip().lower()
        metaphor_scenes.append(scene)
    return metaphor_scenes


def _load_scenes(sb_path: str) -> list:
    with open(sb_path, encoding="utf-8") as f:
        sb = json.load(f)
    if isinstance(sb, list):
        return sb
    return sb.get("scenes", [])


def _comfy_available() -> bool:
    if _ping_comfy():
        return True
    print("  [qwen-metaphor-gen] ⚠️ ComfyUI 未运行，自动拉起...")
    _start_comfy()
    for _ in range(18):
        time.sleep(5)
        if _ping_comfy():
            print("  [qwen-metaphor-gen] ✅ ComfyUI 已拉起")
            return True
    print("  [qwen-metaphor-gen] ❌ ComfyUI 拉起失败，降级兜底")
    return False


def _ping_comfy() -> bool:
    try:
        urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=COMFY_TIMEOUT)
        return True
    except Exception:
        return False


def _start_comfy():
    import subprocess
    try:
        subprocess.Popen(
            ["comfy", "--skip-prompt", "--workspace", "E:/comfyui", "launch", "--background"],
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd="E:/comfyui",
        )
    except Exception as e:
        print(f"  [qwen-metaphor-gen] ⚠️ 拉起 ComfyUI 失败: {e}")


def _free_comfy_vram():
    try:
        req = urllib.request.Request(
            f"{COMFY_URL}/free",
            data=json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        print("  [qwen-metaphor-gen] ♻️ 已释放 ComfyUI 显存")
    except Exception as e:
        print(f"  [qwen-metaphor-gen] ⚠️ 释放显存失败: {e}")


def _qwen_ready() -> bool:
    unet = (_COMFY_MODELS / "diffusion_models" / "qwen_image_2.1_int8_convrot.safetensors").exists()
    clip = (_COMFY_MODELS / "text_encoders" / "qwen3vl_8b_int8_convrot.safetensors").exists()
    vae = (_COMFY_MODELS / "vae" / "qwen_image_2.1_vae_bf16.safetensors").exists()
    return all([unet, clip, vae])


def _generate_image(prompt: str, save_path: str) -> bool:
    if not _qwen_ready():
        print("  [qwen-metaphor-gen] ⚠️ Qwen 模型文件缺失")
        return False
    wf = json.loads(json.dumps(QWEN_WORKFLOW))  # deep copy
    wf["4"]["inputs"]["prompt"] = prompt
    wf["4"]["inputs"]["negative_prompt"] = METAPHOR_NEGATIVE_PROMPT
    wf["5"]["inputs"]["seed"] = uuid.uuid4().int % 100000
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
        return _wait_and_fetch(prompt_id, save_path, timeout=180)
    except Exception as e:
        print(f"  [qwen-metaphor-gen] ComfyUI 调用失败: {e}")
        return False


def _wait_and_fetch(prompt_id: str, save_path: str, timeout: int = 180) -> bool:
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
