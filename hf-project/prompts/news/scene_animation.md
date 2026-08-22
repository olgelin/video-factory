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

### 6. Ken Burns
`tl.from(".scene", {scale:1.06, x:-8, duration:8, ease:"none"}, 0);`

### 7. mix-blend-mode 光晕
`background:radial-gradient(ellipse at 30% 40%, rgba(108,140,255,0.12), transparent 70%); mix-blend-mode:screen;`

| 场景 | 推荐组合 |
|------|---------|
| quote_hero | 逐字渐入 + Ken Burns + 双层发光 |
| data_impact | blur dissolve 卡片 + 毛玻璃 + 遮罩揭示 |
| compare | 遮罩揭示 + 双层发光数字 |
| timeline_event | 逐字渐入 + mix-blend-mode 光晕 |
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
- 🔴 关键信息落定后 hold ≥1s：主标题/大数字/核心内容入场落定后，先静止至少 1 秒（不呼吸、不抖动、不缩放），让观众看清，之后才开始呼吸微动。呼吸动画起始时间 = 入场结束 + 1s（如入场 0.8s 结束，呼吸从 1.8s 才开始）。氛围元素（粒子雨/扫光/光晕）不受此限，可从入场后持续动。
- 粒子雨：
  `tl.to('.p-near',{y:1200,opacity:0.3,duration:4,repeat:3,ease:'none'}, 0);`
  `tl.to('.p-mid',{y:1000,opacity:0.25,duration:7,repeat:1,ease:'none'}, 0);`
  `tl.to('.p-far',{y:800,opacity:0.15,duration:11,repeat:1,ease:'none'}, 0);`
- 扫光多样性：除左→右外，可对角线、中心扩散、往返。避免全同一方向
