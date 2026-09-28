## 🎬 高级技法（每个场景 ≥2 个）

### 1. 逐字渐入（主标题必用）
`<span style="display:inline-block">字</span>` + `tl.from("#main-title span", {opacity:0, y:40, rotationX:-90, stagger:0.04, duration:0.5, ease:"back.out(1.7)"}, 0.2);`

### 2. 毛玻璃卡片
`background:rgba(15,15,46,0.6); backdrop-filter:blur(20px) saturate(180%); border:1px solid rgba(108,140,255,0.15); border-radius:16px;`

### 3. 遮罩揭示
初始 `clip-path:inset(0 100% 0 0)` → `tl.to("#id", {clipPath:"inset(0 0% 0 0)", duration:0.7, ease:"power3.inOut"}, 0.3);`

### 4. 双层发光
`text-shadow: 0 0 20px #6C8CFF, 0 0 60px rgba(108,140,255,0.4);`

### 5. blur dissolve
`tl.from("#card", {filter:"blur(12px)", opacity:0, y:30, duration:0.6, ease:"power2.out"}, 0.3);`

### 6. 数字滚动（大数字必用，冲击力核心）
`tl.from("#num", {textContent:0, duration:1.2, ease:"power1.out", snap:{textContent:1}}, 0.5);` + 配合 scale `tl.from("#num", {scale:2.5, opacity:0, duration:0.5, ease:"back.out(2)"}, 0.3);` —— 大数字先 scale:2.5→1 砸进来，再滚动到目标值，双重冲击。

### 7. 图表生长（数据场景必用）
- 柱状图：`tl.from(".bar", {scaleY:0, transformOrigin:"bottom", stagger:0.1, duration:0.6, ease:"power2.out"}, 0.4);`
- 折线/趋势线：SVG `stroke-dasharray` + `stroke-dashoffset` 从全隐藏到 0，`tl.to("#line", {strokeDashoffset:0, duration:0.8, ease:"power2.inOut"}, 0.5);`
- 圆环仪表：`tl.from("#ring", {strokeDashoffset:<周长>, duration:0.8}, 0.4);`

### 8. Ken Burns
`tl.from(".scene", {scale:1.06, x:-8, duration:8, ease:"none"}, 0);`

| 场景 | 推荐组合 |
|------|---------|
| quote_hero | 逐字渐入 + Ken Burns + 双层发光 |
| data_impact | 数字滚动 + 图表生长 + blur dissolve 卡片 + 毛玻璃 |
| compare | 数字滚动 + 遮罩揭示 + 双层发光数字 |
| timeline_event | 逐字渐入 + 双层发光 |
| list_alert | blur dissolve 逐项 + 毛玻璃卡片 |
| flow | 遮罩揭示节点 + Ken Burns |

## 🆕 每类场景的加分细节

| 场景 | 加分项 |
|------|-------|
| data_impact | 下半屏加趋势线(SVG折线3-4点)或渠道图标，避免∞/KPI上方满下方空 |
| list_alert | 卡片之间加箭头/连接线形成"事态升级"递进感。最后一张加"🔥 正在扩散"标签 |
| compare | 分割线从中心向两端生长。两侧元素 stagger 交替出现 |
| flow | 节点间加 CSS 粒子流连接。轨道元素加渐变 opacity（近中心亮、远暗）模拟深度 |
| timeline_event | 粒子向主体汇聚或从主体发散。主体持续呼吸动画 |
| hud | 中景加 CSS 六边形蜂窝网格或防御环层叠，避免画面太空 |
| quote_hero | 碎裂/飞散后的碎片持续浮动(tl.to repeat:3 yoyo:true)保持紧张感 |

## 基础动效规范

- 入场：tl.from/tl.fromTo，stagger 0.12-0.15s，层次感
- 缓动：内容 power3.out/back.out(1.7) | 呼吸 sine.inOut | 粒子/扫光 none
- 呼吸动画 2-3 个：tl.to repeat:3 yoyo:true
- 🔴 关键信息落定后 hold ≥1s：主标题/大数字/核心内容入场落定后，先静止至少 1 秒（不呼吸、不抖动、不缩放），让观众看清，之后才开始呼吸微动。呼吸动画起始时间 = 入场结束 + 1s（如入场 0.8s 结束，呼吸从 1.8s 才开始）。氛围元素（信息卡内的小光点/扫光）不受此限，可从入场后持续动。
- 🔴 **粒子/星空做「半透明氛围层」**（z-index:1 + alpha:true + opacity 0.3-0.5，叠在隐喻图上，详见 scene_threejs.md），不是实底背景盖图。mix-blend-mode 光晕仍禁用（会叠乱隐喻图）。装饰（小光点/局部扫光/卡片边缘光）做在信息卡内。
- 扫光（仅信息卡内局部）：可对角线、中心扩散、往返，作用在标题/数据卡上，不整屏铺。
