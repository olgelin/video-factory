---
name: topic_selector
description: Video factory skill - topic_selector
version: 3.8
---

# topic_selector

## 概述
视频工厂pipeline的topic_selector步骤。

## 输入
- context: dict - pipeline上下文

## 输出
- context: dict - 更新后的上下文

## 使用方法
```python
from skills.topic_selector.impl import run
result = run(context)
```
