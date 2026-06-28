---
name: color_grader
description: 电影级色彩分级 — 选配色方案 + LUT模拟 + 暗角/颗粒/宽银幕参数
inputs: storyboard.json, design_system 输出
outputs: color_grade.json
version: v1.0
---

# Color Grader

## 职责
为整个视频选定**一套**顶级配色方案，并输出电影级后期处理参数（色彩分级覆盖层、暗角、胶片颗粒、宽银幕黑边）。

**关键原则**：配色是视频级别的，全片统一。不同场景可以有不同的亮度/对比度微调，但色调一致。

## 输入
- `storyboard.json` — 分镜数据（读取 mood/情绪字段）
- design_system 输出（`context["_design_md"]`）— 装饰语言偏好

## 输出
- `color_grade.json` 写入 output/ 目录
- 写回 `context["color_grade"]` 和 `context["color_grade_path"]`

## 配色方案库（4套赛博/科技）

| 方案名 | 背景 | 主色 | 强调色 | 文字 |
|--------|------|------|--------|------|
| blade_runner | #0A0A2E | #00FFFF | #FF00FF | #E0E0FF |
| holographic | #020B1A | #00FF41 | #FFB000 | #CCFFCC |
| neon_noir | #0A0A0A | #FCEE09 | #FF007F | #F0F0F0 |
| apple_dark | #000000 | #0071E3 | #AF52DE | #F5F5F7 |

## 实现要点
- LLM 根据 storyboard 的 mood 选择最合适的配色方案
- 输出包含 CSS 可用的 gradient、blend-mode 等技术参数
- 默认启用：暗角 + 颗粒 + 宽银幕黑边
- 可选启用：扫描线（赛博风格建议开）
