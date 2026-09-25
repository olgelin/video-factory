---
name: qwen_metaphor_gen
description: "VOX 视觉隐喻静帧生成器：读 storyboard 的 metaphor 字段，用 Qwen Image 2.1 把抽象隐喻具象化成写实静帧（B-roll）。隐喻图作背景层，HTML 信息卡叠上面。"
---

# qwen_metaphor_gen — VOX 视觉隐喻静帧生成器（B-roll）

## 职责
- 读 `storyboard.json`，提取每个场景的 `metaphor`（core_metaphor + key_objects）
- 用 Qwen Image 2.1 把抽象隐喻**具象化**成一幅写实静帧（16:9，无文字），存 `output/metaphor/beat-{scene_id}.png`
- 隐喻图作为场景的**视觉主体（背景层）**，HTML 信息卡叠在上面

## 为什么有它（关键架构认知）
storyboard 已经能设计出很好的"视觉隐喻"（文字层），但 hf_builder 用 HTML/CSS/GSAP **画不出具象隐喻**（公章、传送带、骨牌、地砖塌陷）——HTML 只能画抽象信息卡。所以具象隐喻画面必须交给生图模型（Qwen）来做，这就是 B-roll 静帧。

## 与 atmosphere_gen 的分工
- `qwen_metaphor_gen`：**具象隐喻静帧**（主力），Qwen 照着隐喻画写实画面
- `atmosphere_gen`：**抽象氛围底图**（兜底），Krea 画纯氛围，隐喻图失败时回退

## 关键设计
- **无文字硬约束**：隐喻图是背景层，文字由 HTML 叠上去，图里有文字会跟 HTML 冲突（negative prompt 强压制）
- **16:9 非正方形**：用自定义节点 `EmptyQwenImage21Latent` 生成 16:9 latent
- **降级兜底**：ComfyUI 不可用 → 跳过，hf_builder 回退 atmosphere_gen 氛围图
- **显存释放**：生图后调 `/free`
