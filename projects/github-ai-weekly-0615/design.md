# Design System — GitHub AI周榜 06/15

## Visual Identity
- **Style**: Data Drift — 科技数据风
- **Primary BG**: #0f0f1a (深邃暗蓝)
- **Accent 1**: #7c3aed (紫色/科技感)
- **Accent 2**: #06b6d4 (青色/数据感)
- **Accent 3**: #f59e0b (金色/高亮star数)
- **Text**: #e2e8f0 (主文字), #94a3b8 (次要文字)
- **Card BG**: rgba(124,58,237,0.08) with border rgba(6,182,212,0.3)

## Layout Rules
- 横屏 1920x1080
- 每场景2-5个装饰层 + GSAP动画
- Grid卡片占满屏幕，饱满丰富
- 流光背景 + 粒子效果
- 数据字体: JetBrains Mono
- 场景间必须有转场
- 禁止CSS opacity:0，用GSAP tl.set()设置初始状态

## Typography
- 标题: 48px bold, #e2e8f0
- 项目名: 36px bold, #7c3aed
- Star数: 42px JetBrains Mono, #f59e0b
- 描述: 24px, #94a3b8
- 数据标签: 18px JetBrains Mono, #06b6d4

## Data Visualization
- Star增长用动态柱状图
- 项目排名用编号badge
- 每个项目用独立卡片展示
