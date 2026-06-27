# Video Factory V5.3 — 架构参考（借鉴 OpenMontage + Open-Design）

## 借鉴来源

### 1. OpenMontage — Agentic Video Production System
- **12 pipelines**: 声明式 YAML pipeline 定义（我们已有 `short_video.yaml`）
- **52 tools**: 独立可测试的工具（我们的 `tools/` 目录：transcriber/voxcpm/acestep）
- **500+ agent skills**: 可组合的 prompt+tool 组合（我们的 `skills/` 目录）
- **Pipeline-as-Code**: 每条 pipeline 是 YAML → 我们已实现

### 2. Open-Design — Design System Alternative
- **142+ design systems**: 预设配色/字体/间距/动效（我们已有 12 种）
- **Design tokens**: 结构化 JSON/YAML tokens（我们的 `design_system/impl.py` PRESET_STYLES）
- **AI-guided design**: LLM 根据内容选择设计系统（我们的 `design_system` skill）
- **Skill-based generation**: 每个 skill 是特定 UI 模式的 prompt 模板

## V5.3 架构对比

| 模块 | V5.2 | V5.3 | 借鉴自 |
|------|------|------|--------|
| 模型路由 | 全部用 pro | 按任务分配 flash/glm/pro | OpenMontage multi-model |
| hf_builder | 串行 90min | 并行 5 模型 15-20min | OpenMontage parallel tools |
| 转录 | FunASR (差) | faster-whisper (词级时间戳) | 研究推荐 |
| SRT 对齐 | 按字符数均匀 | voice_gen 真实 segment | 自研 |
| 设计系统 | 12 种预设 | 12 种 + motion 模板库 | Open-Design |
| 质量评分 | 无 | 6 维度 0-100 逐场景 | Open-Design validation |
| Pipeline 步骤 | 14 步 | 15 步（+quality_scorer） | OpenMontage composable |

## 可继续借鉴的方向

### OpenMontage
1. **Tool Registry**: 统一工具注册/发现机制（当前 `tool_runner.py` 是硬编码）
2. **Pipeline Versioning**: 每条 pipeline 有版本号，支持 A/B 测试
3. **Skill Marketplace**: 可分享/安装的 skill 包（类似 ClawHub）
4. **Agent Orchestrator**: 多 agent 协作（导演+质检+交付）

### Open-Design
1. **Design Token Validator**: 自动检查 HTML 是否符合 design.md 规范
2. **Visual Regression**: 渲染前后对比，检测视觉退化
3. **Component Library**: 可复用的 HTML 组件（数据卡片/进度条/图表）
4. **Theme Switcher**: 一键切换设计系统（如 cyber_tech → luxury_dark）

## 下一步建议

1. **Tool Registry** — 把 `tool_runner.py` 重构为注册表模式
2. **Component Library** — 从 `scene_templates.py` 提取可复用组件
3. **Visual Regression** — 在 quality_checker 中加入前后对比
4. **Pipeline A/B** — 支持同一话题用不同设计系统渲染对比
