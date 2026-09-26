# h3_director — 隐喻静帧 → 动态 B-roll

> ⚠️ **状态（2026-09-27）：已回退，暂不启用。** 端到端验证结论——动态 B-roll 增量价值有限：①信息卡必须叠在背景上→压暗遮罩会模糊画面→"镜头运动"这个唯一卖点看不清；②Three.js bg3d 背景(z-index:1)会盖住 video(z-index:0)，只有无 bg3d 的场景才显示；③文字漂移（招牌类隐喻无法完全无文字）。对比"静态隐喻图+ken burns"（清晰、稳定、秒级），动态 B-roll 不划算。**技术已全部验证跑通并存证于此，以后图生视频模型更快/更好时，把 vox.yaml 的 h3_director stage 加回即可启用。** 启用前需解决：video z-index 提高到 bg3d 之上、减轻暗化、从源头无文字。

用 MiniMax H3 导演台（ref2va + ref2v turbo 8step + SelfLift）把 qwen_metaphor_gen 的隐喻静帧变成「有镜头运动的动态 B-roll」，让画面从「静态图 + ken burns」升级为「真正的视频镜头」。

## 职责与分工

| 模块 | 负责 | 产物 |
|---|---|---|
| storyboard | 设计隐喻 + 镜头语言（camera_motion） | storyboard.json |
| qwen_metaphor_gen | 隐喻 → 无文字静帧（主力） | output/metaphor/beat-*.png |
| **h3_director**（本 skill） | 静帧 → 动态 B-roll（镜头运动） | output/broll/beat-*.mp4 |
| hf_builder | 动态 B-roll 或静态图注入背景 + HTML 信息卡 | 最终画面 |

## 核心设计（源自 MiniMax 官方 prompt 体系调研）

1. **运镜三要素**：把 storyboard 的 `camera_motion` 翻译成 H3 官方运镜句（运动类型 + 幅度 + 速度），如 `dolly_in` → `The camera pushes in with small amplitude at slow speed`。B-roll 空镜统一 small amplitude + slow speed（最稳、最有导演感）。
2. **六段式 Ref2VA prompt**（`ref-en.txt` 结构）：`subject_definitions → summary → retention_analysis → detailed_description → overall_soundscape → non_diegetic_music`，字段顺序固定。`retention_analysis` 里 `<Picture 1> fully_preserved` 钉死首帧一致性。
3. **首帧引导**：`<Picture 1>` = 隐喻静帧，`summary: keyframe completion, the shot begins from <Picture 1>`。
4. **no text 硬约束**：B-roll 是背景层，文字由 HTML 信息卡叠上去，图里不能有字。
5. **提速**：ref2va + ref2v turbo 8step lora + SelfLift 二采，实测 503s → 173s（约 2.9 倍）。

## 降级兜底

- ComfyUI 不可用 / H3 模型缺失 / 生成失败 → `broll_available=False`，hf_builder 回退「静态隐喻图 + ken burns」（当前已稳定路径）。

## 坑

- **文字漂移**：首帧静帧里若有招牌/吊牌文字，H3 I2V 会漂移成伪汉字。根治法 = 从源头让静帧无文字（qwen_metaphor_gen 的 negative prompt 已强化 signage/shop sign/lettering）。
- **模型分线**：图生视频用 ref2va（导演台），不是 fl2va（文生视频）。本地只有 ref2v turbo lora，没有 fl2v。
- **显存**：H3 全套约 14GB，跑完调 `/free` 释放，否则影响后续 Qwen 加载。
- **timeline_data**：version 9 schema，图片走 `images` 数组 + `segmentConfig.segments[].images` 引用，`<Picture N>` 对应 `ref_image_N-1`。
