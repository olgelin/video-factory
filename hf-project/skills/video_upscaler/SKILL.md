---
name: video_upscaler
description: "Video2X 高清修复（可选）。1080p → 超分输出"
tags: ["video", "enhance", "optional"]
version: "1.0"
---

# video_upscaler

## 概述
使用 Video2X 对 step10_video.mp4 进行超分辨率重建，输出 step13_upscaled.mp4。可选步骤。

## 输入
- output/step10_video.mp4

## 输出
- output/step13_upscaled.mp4

## 使用方法
```python
from skills.video_upscaler.impl import run
result = run(context)
```
