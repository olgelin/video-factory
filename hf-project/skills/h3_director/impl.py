"""h3_director/impl.py — 隐喻静帧 → 动态 B-roll（MiniMax H3 导演台 I2V）

读 storyboard 的隐喻 + qwen_metaphor_gen 的静帧（output/metaphor/beat-*.png），
用 H3 导演台（ref2va + ref2v turbo 8step + SelfLift）把静帧变成有镜头运动的动态 B-roll。

核心（源自 MiniMax 官方 prompt 体系 + TimelineDirector v9 schema 调研）：
- 运镜 = H3 三要素（运动类型 + 幅度 + 速度），把 storyboard 的 camera_motion 翻译成运镜句
- 六段式 Ref2VA prompt（subject_definitions→non_diegetic_music）——治文字漂移 + 导演感
- no text 显式约束（B-roll 空镜，文字由 HTML 信息卡叠上去）
- 首帧引导（<Picture 1> = 隐喻静帧），ref2va + ref2v turbo 8step + SelfLift 二采提速

输入：output/storyboard.json + output/metaphor/beat-*.png
输出：output/broll/beat-{scene_id}.mp4
只在 vox 管线被调用；ComfyUI 不可用或 H3 模型缺失则降级跳过（hf_builder 回退静态隐喻图 + ken burns）
"""

import json
import os
import time
import uuid
import shutil
import urllib.request
from pathlib import Path

COMFY_URL = "http://127.0.0.1:8188"
COMFY_TIMEOUT = 3
INPUT_DIR = Path("E:/comfyui/input")
_MODELS = Path("E:/comfyui/models")

# 导演台 workflow（ref2va + ref2v turbo 8step + SelfLift），timeline_data 在 run 里动态填
DIRECTOR_WORKFLOW = {
    "1": {"class_type": "UNETLoader", "inputs": {
        "unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
    "11": {"class_type": "LoraLoaderModelOnly", "inputs": {
        "model": ["1", 0],
        "lora_name": "minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors",
        "strength_model": 1.0}},
    "2": {"class_type": "CLIPLoader", "inputs": {
        "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
    "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
    "5": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
    "6": {"class_type": "BasicScheduler", "inputs": {
        "model": ["11", 0], "scheduler": "simple", "steps": 8, "denoise": 1.0}},
    "7": {"class_type": "MiniMaxH3TimelinePlanner", "inputs": {
        "width": 960, "height": 544, "generation_seconds": 5.0, "timeline_data": ""}},
    "8": {"class_type": "MiniMaxH3FiniteSegmentSampler", "inputs": {
        "model": ["11", 0], "clip": ["2", 0], "vae": ["3", 0], "audio_vae": ["4", 0],
        "finite_plan": ["7", 2], "sampler": ["5", 0], "sigmas": ["6", 0], "seed": 42,
        "continue_audio_latent": True, "ref_image_size": "match"}},
    "9": {"class_type": "CreateVideo", "inputs": {
        "images": ["8", 1], "audio": ["8", 2], "fps": 24, "bit_depth": 8}},
    "10": {"class_type": "SaveVideo", "inputs": {
        "video": ["9", 0], "filename_prefix": "h3_broll", "format": "mp4"}},
}

# storyboard camera_motion → H3 三要素运镜句（运动类型 + 幅度 + 速度）
# B-roll 空镜统一 small amplitude + slow speed：最稳、最有导演感
CAMERA_MOTION_MAP = {
    "dolly_in": "The camera pushes in with small amplitude at slow speed",
    "dolly_out": "The camera pulls out with small amplitude at slow speed",
    "zoom_in": "The camera zooms in with small amplitude at slow speed",
    "zoom_out": "The camera zooms out with small amplitude at slow speed",
    "pan_left": "The camera pans left with small amplitude at slow speed",
    "pan_right": "The camera pans right with small amplitude at slow speed",
    "tilt_up": "The camera tilts up with small amplitude at slow speed",
    "tilt_down": "The camera tilts down with small amplitude at slow speed",
    "static": "The camera holds a static shot",
}

# 六段式 Ref2VA prompt（官方 ref-en.txt 结构，字段顺序固定）
REF2VA_PROMPT_TEMPLATE = (
    "subject_definitions: <Picture 1> is a cinematic editorial illustration, deep blue and purple "
    "gradient palette with neon cyan accents, clean modern tech style.\n"
    "summary: keyframe completion, the shot begins from <Picture 1>.\n"
    "retention_analysis: <Picture 1> ([Shot 1] first frame): fully_preserved.\n"
    "detailed_description: [Shot 1] {camera_motion}. The scene stays compositionally consistent "
    "with the first frame, subtle atmospheric motion, cinematic depth. "
    "no text, no captions, no watermark, no logo, no letters.\n"
    "overall_soundscape: faint ambient hum, subtle spatial reverb.\n"
    "non_diegetic_music: N/A"
)


def run(context: dict) -> dict:
    project_root = Path(context.get("project_root", Path(__file__).parent.parent.parent))
    output_dir = project_root / "output"
    broll_dir = output_dir / "broll"

    # 1. 环境检查（不可用则降级，不报错）
    if not _comfy_available():
        print("  [h3-director] ⚠️ ComfyUI 不可用，跳过动态 B-roll（回退静态隐喻图 + ken burns）")
        context["broll_available"] = False
        return context
    if not _h3_ready():
        print("  [h3-director] ⚠️ H3 ref2va 模型缺失，跳过动态 B-roll")
        context["broll_available"] = False
        return context

    # 2. 读 storyboard
    sb_path = context.get("storyboard_path") or str(output_dir / "storyboard.json")
    if not os.path.exists(sb_path):
        context["broll_available"] = False
        return context
    scenes = _load_scenes(sb_path)
    metaphor_scenes = [s for s in scenes if (s.get("metaphor") or {}).get("core_metaphor")]
    # 测试限流：H3_BROLL_LIMIT 环境变量限制生成场景数（默认 0=全量）
    _limit = int(os.environ.get("H3_BROLL_LIMIT", "0") or "0")
    if _limit > 0:
        metaphor_scenes = metaphor_scenes[:_limit]
        print(f"  [h3-director] 限流：只生成前 {_limit} 个场景")
    if not metaphor_scenes:
        context["broll_available"] = False
        context["broll_scenes"] = []
        return context

    # 3. 逐个场景生成动态 B-roll
    broll_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    broll_scenes = []
    for scene in metaphor_scenes:
        sid = scene.get("scene_id", 1)
        still = output_dir / "metaphor" / f"beat-{sid}.png"
        if not still.exists():
            print(f"  [h3-director] ⚠️ beat-{sid}.png 静帧缺失，跳过")
            continue
        motion = scene.get("camera_motion", {})
        motion_type = motion.get("type", "") if isinstance(motion, dict) else str(motion or "")
        camera_sentence = CAMERA_MOTION_MAP.get(motion_type, CAMERA_MOTION_MAP["static"])
        prompt = REF2VA_PROMPT_TEMPLATE.format(camera_motion=camera_sentence)
        out_mp4 = broll_dir / f"beat-{sid}.mp4"
        ok = _generate_broll(str(still), prompt, str(out_mp4))
        if ok:
            generated += 1
            broll_scenes.append(sid)
            print(f"  [h3-director] ✅ beat-{sid}.mp4（{motion_type or 'static'}）")
        else:
            print(f"  [h3-director] ⚠️ beat-{sid}.mp4 生成失败")
        time.sleep(1)

    context["broll_available"] = generated > 0
    context["broll_dir"] = str(broll_dir)
    context["broll_scenes"] = broll_scenes
    print(f"  [h3-director] 完成：{generated}/{len(metaphor_scenes)} 段动态 B-roll")

    _free_comfy_vram()
    return context


# ── 内部函数 ──

def _load_scenes(sb_path: str) -> list:
    try:
        with open(sb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        scenes = data.get("scenes", data) if isinstance(data, dict) else data
        if isinstance(scenes, dict):
            scenes = list(scenes.values())
        return scenes if isinstance(scenes, list) else []
    except Exception:
        return []


def _comfy_available() -> bool:
    try:
        urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=COMFY_TIMEOUT)
        return True
    except Exception:
        return False


def _h3_ready() -> bool:
    unet = (_MODELS / "diffusion_models" / "minimax_h3_ref2va_pruned_int8_convrot.safetensors").exists()
    clip = (_MODELS / "text_encoders" / "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors").exists()
    vae = (_MODELS / "vae" / "minimax_h3_video_vae_fp16.safetensors").exists()
    return all([unet, clip, vae])


def _generate_broll(still_path: str, prompt: str, save_path: str) -> bool:
    """把静帧复制到 input，提交导演台 workflow（首帧引导），下载生成的视频。"""
    img_name = f"h3_broll_{Path(still_path).stem}.png"
    try:
        shutil.copy(still_path, str(INPUT_DIR / img_name))
    except Exception as e:
        print(f"  [h3-director] 复制静帧失败: {e}")
        return False

    timeline_data = {
        "version": 9, "fps": 24,
        "globalPrompt": prompt,
        "secondPass": True,
        "secondPassModel": "minimax_h3_latent_upscaler_3d_conv_v1_bf16.safetensors",
        "images": [{"id": "img-1", "file": img_name}],
        "segmentConfig": {
            "count": 1, "activeIndex": 0, "mode": "timeline",
            "segments": [{"startFrame": 0, "endFrame": 124, "images": ["img-1"], "audios": [], "prompt": ""}],
        },
    }
    wf = json.loads(json.dumps(DIRECTOR_WORKFLOW))
    wf["7"]["inputs"]["timeline_data"] = json.dumps(timeline_data, ensure_ascii=False)

    try:
        payload = {"prompt": wf, "client_id": str(uuid.uuid4())}
        req = urllib.request.Request(
            f"{COMFY_URL}/prompt", data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=30)
        r = json.loads(resp.read().decode())
        prompt_id = r.get("prompt_id")
        if not prompt_id:
            return False
        return _wait_and_fetch_video(prompt_id, save_path, timeout=420)
    except Exception as e:
        print(f"  [h3-director] ComfyUI 调用失败: {e}")
        return False


def _wait_and_fetch_video(prompt_id: str, save_path: str, timeout: int = 420) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
            data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
            entry = data.get(prompt_id, {})
            status = entry.get("status", {}).get("status_str", "")
            if status == "success":
                for node_outputs in entry.get("outputs", {}).values():
                    for v in node_outputs.get("images", []):
                        url = f"{COMFY_URL}/view?filename={v['filename']}&subfolder={v.get('subfolder','')}&type={v.get('type','output')}"
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        with open(save_path, "wb") as f:
                            f.write(urllib.request.urlopen(urllib.request.Request(url), timeout=60).read())
                        return True
                return False
            elif status in ("error", "failed"):
                return False
        except Exception:
            pass
        time.sleep(3)
    return False


def _free_comfy_vram():
    try:
        req = urllib.request.Request(
            f"{COMFY_URL}/free",
            data=json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print("  [h3-director] ♻️ 已释放 ComfyUI 显存")
    except Exception:
        pass
