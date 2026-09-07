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

## 🔴 好话题筛选标准（2026-09-06 用户定）

好话题 = **揭盖子**，不是**翻资料**。让观众"原来如此"，不是"哦知道了"。

| 维度 | 好话题（有内涵）| 垃圾话题（low）|
|---|---|---|
| 信息差/争议 | 揭示不为人知的真相/矛盾/骗局 | 介绍已知事实（"介绍曲阳xxx"）|
| 数据/硬料 | 具体数字（99.9% vs 62.7%、129亿、70%稀土）| 泛泛而谈，无数据 |
| 对立/张力 | 矛盾冲突、认知反差（钞能力 vs 真智能）| 中立平铺 |
| 深层启示 | 有"所以呢"的思考 | 就事论事 |

- ❌ **介绍型**（介绍/科普/带你了解/是什么/有哪些）→ 扣分，浅薄
- ❌ **开放式**（如何看待/未来趋势/有什么影响）→ 扣分，太泛
- ✅ **信息差**（真相/背后/内幕/骗局/争议/为什么/钞能力/落马/暴雷/跑路）→ 加分

硬过滤已入 `core/topic_validator.py`（`INTRO_KEYWORDS` 扣分 + `INSIGHT_KEYWORDS` 加分）。用户给宽泛指令（如"曲阳热点"）时，要自主找到"真正值得的话题"（有争议有数据有深度），不要"介绍曲阳xxx"这种浅薄话题。
