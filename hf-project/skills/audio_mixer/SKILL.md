---
name: audio_mixer
description: Video factory skill - audio_mixer
version: 3.8
---

# audio_mixer

## 概述
视频工厂pipeline的audio_mixer步骤。

## 输入
- context: dict - pipeline上下文

## 输出
- context: dict - 更新后的上下文

## 使用方法
```python
from skills.audio_mixer.impl import run
result = run(context)
```
