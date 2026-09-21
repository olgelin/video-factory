---
name: atmosphere_gen
description: "氛围图生成器：读 storyboard，按 visual_type(构图)+mood(色调) 匹配规则生成英文提示词，调 ComfyUI(Krea-2) 出氛围底图。ComfyUI 不可用则降级兜底。"
---

# atmosphere_gen — 氛围图生成器

## 职责
- 读 `storyboard.json`，对每个场景用 LLM 生成英文 ComfyUI 提示词
- 调 ComfyUI（Krea-2 Turbo 首选，Flux/SDXL 兜底）出 16:9 氛围底图，存 `output/atmosphere/beat-{scene_id}.png`
- **降级兜底**：ComfyUI 服务不可用 → 跳过，hf_builder 回退纯 CSS 背景（管线不崩）

## 背景图匹配规则（核心设计）
背景图是"氛围底图"，衬托前景 HTML 内容，不抢戏。匹配规则在 `prompts/atmosphere_system.md`：
- **visual_type → 构图复杂度**：quote_hero 简洁留白 / data_impact 数据流 / compare 左右分色 / flow 流动线条 / list_alert 暗沉警示 / timeline_event 横向延伸 / hud 网格扫描线
- **mood → 色调**：工业→冷灰金属 / 数据科技→霓虹青蓝 / 法庭→冷峻紫蓝 / 历史→暗金古旧 / 海洋→深蓝 / 警示→暗红橙

## 关键设计
- **生图模型**：Krea-2 Turbo（12.9B/fp8/8步，首选）> Flux > SDXL，`_select_workflow()` 按模型文件自动切换
- **ComfyUI 服务自愈**：`_comfy_available()` ping 失败 → `_start_comfy()` 拉起 → 轮询 90s
- **显存释放**：生图完成后调 `/free` 释放模型缓存（否则占 5-6GB 挤占后续 voxcpm）
- **氛围图"本视频专属"**：每次先清 `output/atmosphere/beat-*.png`，防止不同话题复用旧图串味
- 提示词生成：LLM 批量（一次生成所有场景），失败走 `_fallback_prompt`（按 visual_type 确定性映射）
- 已生成的场景跳过（幂等，重跑不重复出图）

## 环境依赖
- ComfyUI 服务 `http://127.0.0.1:8188`（`comfy --workspace E:/comfyui launch --background`）
- Krea-2 模型 3 文件已在 `E:\comfyui\models\`（diffusion_models/text_encoders/vae）
