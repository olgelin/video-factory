---
name: layout_composer
description: 为每个场景选定布局骨架 + 构图网格 + 景深参数
inputs: storyboard.json, color_grade.json
outputs: layout_plan.json
version: v1.0
---

# Layout Composer

## 职责
为每个场景指定布局骨架（使用哪个模板）并设定构图规则和景深分层参数。

**关键原则**：布局可以不同（保证场景多样性），但构图风格全片统一。

## 输入
- `storyboard.json` — visual_type + key_elements + depth_layers
- `color_grade.json` — 配色方案（影响留白/填充率决策）

## 输出
- `layout_plan.json` → context["layout_plan"]

## 布局骨架库
| visual_type | 模板 | 特征 |
|-------------|------|------|
| data_impact | data_impact | 大数字居中+四角卡片 |
| compare | compare | 左70%右30%双栏 |
| flow | flow | 4节点水平流程+SVG连线 |
| quote_hero | quote_hero | 压轴金句+光晕 |
| list_alert | list_alert | 红色警示条+列表项 |
| timeline_event | timeline_event | 时间轴+4时间点 |

## 景深系统
- 背景层：scale(0.85), blur(8px), 低速视差
- 中景层：scale(1.0), blur(0), 核心内容
- 前景层：scale(1.2), blur(4px), 装饰元素
