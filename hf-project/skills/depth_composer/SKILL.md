---
name: depth_composer
description: 分配 z-index 层级 + 视差倍率 + 装饰元素位置
inputs: layout_plan.json, motion_plan.json, color_grade.json
outputs: depth_plan.json
version: v1.0
---

# Depth Composer

## 职责
为所有场景元素分配 z-index 层级，定义视差滚动倍率，以及装饰元素（光效、粒子、网格）的放置位置。

## Z-Index 体系（全片统一）
| 层级 | z-index | 内容 |
|------|---------|------|
| UI覆盖 | 1000 | 字幕（渲染器层面） |
| 暗角 | 900 | vignette overlay |
| 光泄漏 | 800 | light leaks |
| 颗粒 | 700 | film grain |
| 宽银幕 | 600 | letterbox |
| 前景 | 100 | 前景装饰 |
| 核心内容 | 50 | 标题/数据/卡片 |
| 中景 | 10 | 次级信息 |
| 背景装饰 | 5 | 网格/光晕 |
| 背景 | 1 | 纯色底 |

## 视差倍率
| 层 | 速度 |
|----|------|
| Far | 0.2x |
| Mid | 0.5x |
| Close | 0.8x |
| Near (hero) | 1.0x |
