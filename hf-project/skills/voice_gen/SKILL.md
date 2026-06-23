---
name: voice_gen
description: Video factory skill - voice_gen
version: 3.8
---

# voice_gen

## 概述
视频工厂pipeline的voice_gen步骤。

## 输入
- context: dict - pipeline上下文

## 输出
- context: dict - 更新后的上下文

## 使用方法
```python
from skills.voice_gen.impl import run
result = run(context)
```
