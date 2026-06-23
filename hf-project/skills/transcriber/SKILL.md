---
name: transcriber
description: Video factory skill - transcriber
version: 3.8
---

# transcriber

## 概述
视频工厂pipeline的transcriber步骤。

## 输入
- context: dict - pipeline上下文

## 输出
- context: dict - 更新后的上下文

## 使用方法
```python
from skills.transcriber.impl import run
result = run(context)
```
