---
name: video_renderer
description: Video factory skill - video_renderer
version: 3.8
---

# video_renderer

## 概述
视频工厂pipeline的video_renderer步骤。

## 输入
- context: dict - pipeline上下文

## 输出
- context: dict - 更新后的上下文

## 使用方法
```python
from skills.video_renderer.impl import run
result = run(context)
```
