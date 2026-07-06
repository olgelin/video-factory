---
name: quality_gate
description: "V6.0 统一质量关卡（合并 quality_scorer + quality_checker）。HTML 评分 → 视频质检"
tags: ["quality", "validate", "merged"]
version: "6.0"
---

# quality_gate

## 概述
两阶段质量关卡：先对 HTML 做结构分析 + 视觉丰富度评分，再对最终视频做 ffprobe 质检 + 帧采样 + 音频分析。

## 输入
- hf_render_project_v2/compositions/*.html
- output/storyboard.json
- output/step11_final.mp4

## 输出
- output/quality_report.json

## 使用方法
```python
from skills.quality_gate.impl import run
result = run(context)
```
