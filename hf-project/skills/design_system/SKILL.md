---
name: design_system
description: "生成视觉设计系统（配色方案、字体、风格方向）。输出 design.md + design_specs.json"
tags: ["design", "visual", "pipeline"]
version: "1.0"
---

# design_system

## 概述
根据 topic 和 script 生成视觉设计系统，包括配色方案、字体选择、风格方向，供后续 storyboard 和 hf_builder 使用。

## 输入
- context: dict — 含 topic, step03_script.json

## 输出
- output/design.md — 设计系统 Markdown
- output/design_specs.json — 每个场景的设计规格

## 使用方法
```python
from skills.design_system.impl import run
result = run(context)
```
