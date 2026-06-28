---
name: motion_director
description: 为每个场景设计镜头运动和文字动画时间线
inputs: layout_plan.json, storyboard.json, color_grade.json
outputs: motion_plan.json
version: v1.0
---

# Motion Director

## 职责
设计每个场景的：
1. 镜头运动（推/拉/摇/移）
2. 文字入场动画（逐字/模糊→清晰/弹性落地）
3. ease 曲线选择

## 镜头运动库
| 运动 | GSAP参数 | 适用场景 |
|------|---------|---------|
| dolly_in | translateZ(-200→0), perspective(1200px) | 开场/冲击 |
| dolly_out | translateZ(0→-200) | 结尾/拉开空间 |
| crane_down | y: -30→0 | 标题下落 |
| truck_right | x: -40→0 | 侧入 |
| dutch_tilt | rotateZ: ±3° | 紧张/不安 |
| static | 无移动 | 数据展示 |

## 文字动画库
| 类型 | GSAP配置 | 适用 |
|------|---------|------|
| stagger_blur | chars: {blur:10→0, y:50→0, stagger:0.03} | 标题 |
| fade_up | {opacity:0→1, y:30→0} | 副标题 |
| scale_bounce | {scale:0→1.05→1, ease:back.out(1.7)} | 数字 |
| glitch_in | {x:±5, opacity:0→1, repeat:3} | 赛博 |
| typewriter | width:0→100%, steps | 代码风格 |
