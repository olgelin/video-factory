---
name: visual_director
description: "V6.0 电影级视觉导演（合并 color_grader + layout_composer + motion_director + depth_composer）"
tags: ["design", "visual", "merged"]
version: "6.0"
---

# visual_director

## 概述
统一视觉导演——读 storyboard.json 的 mood/concept/depth_layers，一步产出 visual_plan.json（含 color/layout/motion/depth 全部维度）。替代 4 个独立视觉 skill 的链式调用。

## 输入
- output/storyboard.json

## 输出
- output/visual_plan.json

## 使用方法
```python
from skills.visual_director.impl import run
result = run(context)
```
