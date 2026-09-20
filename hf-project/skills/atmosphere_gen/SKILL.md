---
name: atmosphere_gen
description: "VOX 氛围图生成器：读 storyboard，用 LLM 生成提示词，调 ComfyUI(SDXL) 出科技风氛围底图。ComfyUI 不可用时降级兜底。"
---

# atmosphere_gen — VOX 氛围图生成器

## 职责
- 读 `storyboard.json`，对每个场景用 LLM 生成英文 ComfyUI 提示词
- 调 ComfyUI（SDXL）出 16:9 科技风氛围底图，存 `output/atmosphere/beat-{scene_id}.png`
- **降级兜底**：ComfyUI 服务不可用 → 跳过，设 `context["atmosphere_available"]=False`，hf_builder 回退纯 CSS 背景（管线不崩）

## 只在 vox 管线生效
- 其他管线（short_video/edu_video/edu_music/speech_to_video）的 yaml 不引用此 skill
- hf_builder 只在 `video_style == "vox"` 且 `atmosphere_available` 时引用氛围图

## 关键设计
- ComfyUI 服务探测：`curl http://127.0.0.1:8188/system_stats`（3s 超时）
- 提示词生成：LLM 批量（一次调用生成所有场景的英文 prompt），失败走固定 fallback
- 出图：内嵌 SDXL workflow（16:9 1024×576），轮询 history 直到 success，下载到 atmosphere/
- 已生成的场景跳过（幂等，重跑不重复出图）

## 环境依赖
- ComfyUI 服务运行在 `http://127.0.0.1:8188`（`comfy --workspace E:/comfyui launch --background`）
- SDXL 模型：`sd_xl_base_1.0.safetensors` 已在 `E:\comfyui\models\checkpoints\`
