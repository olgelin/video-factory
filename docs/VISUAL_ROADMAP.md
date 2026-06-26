# 视觉提升路线图

## 当前状态

video-factory 的视觉由 `hf_builder` 用 LLM 生成 HTML/CSS/GSAP 动画实现。
当前质量：7/10——数据可视化不错，但缺少"电影感"和"层次感"。

## 从 OpenMontage 可借鉴的（HyperFrames 路线适用）

OpenMontage 有大量视觉设计知识，以下是**不依赖 Remotion/AI 视频 API**、可直接用于 HyperFrames 的部分：

### 1. 排版规范（typography.md）

**当前问题**：字体大小、间距、对比度没有统一标准，每个场景 LLM 自由发挥。

**改进方案**：
- 标题 60-90px / 正文 40-60px / 数据 100-140px（1080p 标准）
- 安全区：所有文字在画面 80% 范围内（192px 边距）
- 字体配对：标题用粗体（Montserrat Bold），正文用 Inter/Noto Sans SC
- 对比度：白字黑底 ≥ 4.5:1（WCAG AA 标准）
- 动画缓动：入场用 `easeOutCubic`，禁止 `linear`

**实施**：在 `hf_builder/impl.py` 的 SCENE_PROMPT 中强化排版约束。

### 2. 数据可视化策略（data-visualization.md）

**当前问题**：数据展示方式单一（大数字+进度条），缺少图表类型选择。

**改进方案**：
- 3-9 个数据点 → 柱状图
- 趋势 → 折线图
- 占比 → 饼图（最多 5-6 片）
- KPI → 3-6 个指标卡片网格
- 对比 → 双柱对比 + 差值标注

**实施**：在 `storyboard/impl.py` 中根据数据特征自动推荐图表类型，传递给 `hf_builder`。

### 3. 视觉增强策略（enhancement-strategy.md）

**当前问题**：场景之间切换生硬，缺少过渡和层次。

**改进方案**：
- 转场动画：淡入淡出 0.3s / 滑动 0.5-1.0s
- 覆盖层密度：短内容每 3-5s 一个视觉变化
- 三层结构强化：背景层 → 内容层 → 装饰层（已有，但执行不稳定）
- 文字在画面上的停留时间：至少 1s/13 字符

**实施**：在 `hf_builder` 场景间自动插入转场 HTML，在 `video_renderer` 中做交叉淡入淡出。

### 4. 镜头语言（video-gen-prompting.md 的 5 要素）

虽然 video-factory 不生成 AI 视频，但**镜头语言可以转化为 CSS 动画**：

| 镜头语言 | CSS/GSAP 实现 |
|----------|--------------|
| 推镜头（dolly in） | `scale: 1.0 → 1.15` + `transformOrigin: center` |
| 拉镜头（dolly out） | `scale: 1.2 → 1.0` |
| 摇镜（pan） | `x: -100 → 0` 或 `backgroundPosition` 动画 |
| 浅景深 | `filter: blur(3px)` 背景层 + 清晰前景 |
| 慢动作 | `timeScale: 0.5` 或延长 duration |

**实施**：在 `storyboard` 中为每个场景指定镜头运动，`hf_builder` 转化为 GSAP 动画。

---

## 分阶段实施计划

### Phase 1：排版统一（1-2 天，效果提升 +1 分）

- [ ] 在 `SCENE_PROMPT` 中固化字体大小/间距/对比度标准
- [ ] 强制安全区（80% 画面范围）
- [ ] 统一缓动曲线（禁止 linear）
- [ ] 限制字体种类（最多 2 种）

### Phase 2：数据可视化升级（2-3 天，效果提升 +1 分）

- [ ] `storyboard` 自动推荐图表类型
- [ ] `hf_builder` 支持柱状图/折线图/饼图模板
- [ ] 数据动画：countUp + 柱状生长 + 折线绘制

### Phase 3：转场与层次（2-3 天，效果提升 +1 分）

- [ ] 场景间自动插入转场（淡入淡出/滑动/缩放）
- [ ] 三层结构强制执行（背景/内容/装饰 z-index 校验）
- [ ] 文字停留时间自动计算

### Phase 4：镜头语言（3-5 天，效果提升 +1 分）

- [ ] `storyboard` 增加镜头运动字段
- [ ] `hf_builder` 将镜头语言转化为 GSAP 动画
- [ ] 支持推/拉/摇/跟/浅景深效果

### Phase 5：素材增强（5-7 天，效果提升 +1 分）

- [ ] 接入 Pexels/Pixabay 免费实拍素材作为背景
- [ ] 粒子系统（飘落/光晕/数据流）
- [ ] 3D 透视效果（CSS 3D transforms）

---

## 目标

| 阶段 | 当前分 | 目标分 |
|------|--------|--------|
| 现在 | 7/10 | — |
| Phase 1-2 | — | 8/10 |
| Phase 3-4 | — | 9/10 |
| Phase 5 | — | 9.5/10 |

## OpenMontage 不适合借鉴的部分

| 模块 | 原因 |
|------|------|
| Remotion 渲染 | video-factory 只用 HyperFrames |
| AI 视频生成（Seedance/Kling/Veo） | 成本高 + 风格不可控 |
| 实拍素材剪辑流程 | 资讯短视频不需要 |
| 口播人物（TalkingHead） | 无人物出镜需求 |
| 参考视频分析 | 不需要模仿其他视频风格 |
