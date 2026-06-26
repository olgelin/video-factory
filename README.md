# 🎬 Video Factory v5

AI 驱动的短视频自动化生产流水线 — 从热点采集到成品视频，13 步全自动。

## 🚀 快速开始

### 环境要求
- Python 3.11+ / FFmpeg / Node.js 22+ (HyperFrames)
- 火山引擎 Ark API Key（LLM 调用）

### 运行

```bash
cd video-factory

# 完整跑一条（自动选题→成品视频）
python run.py

# 指定话题
python run.py --topic "你的话题"

# 只跑渲染（前面步骤已有产出）
python run.py --topic "你的话题" --steps 10-12

# 竖屏模式
python run.py --topic "你的话题" --vertical

# 列出可用 pipeline
python run.py --list
```

## 📁 项目结构

```
video-factory/
├── run.py                          ← 新入口（推荐）
├── pipeline_loader.py              ← YAML 驱动执行引擎
├── pipeline_defs/
│   └── short_video.yaml            ← Pipeline 定义（改流程改这里）
├── hf-project/
│   ├── provider.py                 ← LLM Provider 抽象（自动发现+智能路由）
│   ├── cost_tracker.py             ← API 费用追踪
│   ├── llm_utils.py                ← 向后兼容层
│   ├── skills/                     ← 13 个独立 skill
│   │   ├── topic_scout/            ← 热点采集
│   │   ├── topic_selector/         ← 选题评估
│   │   ├── script_writer/          ← 口播脚本
│   │   ├── lyrics_writer/          ← 歌词创作
│   │   ├── voice_gen/              ← VoxCPM2 配音
│   │   ├── transcriber/            ← FunASR 转录+字幕
│   │   ├── bgm_generator/          ← ACE-Step BGM
│   │   ├── design_system/          ← 视觉设计系统
│   │   ├── storyboard/             ← 分镜设计
│   │   ├── hf_builder/             ← HTML 场景生成
│   │   ├── video_renderer/         ← HyperFrames 渲染
│   │   ├── audio_mixer/            ← FFmpeg 音视频混合
│   │   └── video_upscaler/         ← Video2X 高清修复
│   └── output/                     ← 产物目录
├── tools/                          ← 本地工具（各自独立 venv）
│   ├── voxcpm/                     ← VoxCPM2 配音引擎
│   ├── acestep/                    ← ACE-Step 1.5 BGM 引擎
│   ├── transcriber/                ← FunASR 转录引擎
│   └── video2x/                    ← Video2X 高清修复
├── core/                           ← 基础设施
├── docs/                           ← 文档
└── main_full.py                    ← 旧入口（保留兼容）
```

## 🎯 核心特性

- **13 步全自动** — 热点采集→选题→脚本→配音→BGM→设计→分镜→渲染→混音
- **YAML 驱动** — 改流程只需编辑 `pipeline_defs/short_video.yaml`
- **智能 LLM 路由** — 5 个模型自动发现，按任务类型选最优
- **工具隔离** — ACE-Step/VoxCPM/Transcriber 各自独立 venv，升级互不影响
- **费用追踪** — 每次调用自动记录，输出 `cost_log.json`
- **429 保护** — 令牌桶限流 + 自动重试

## 🔧 日常维护

### 换模型
编辑 `E:\Hermes-Agent\config.yaml`：
```yaml
model:
  default: deepseek-v4-pro,deepseek-v4-flash,glm-5.2,minimax-m3
```

### 加新步骤
在 `pipeline_defs/short_video.yaml` 加一段 YAML，然后在 `hf-project/skills/` 下写 `impl.py`。

### 升级本地工具
```bash
cd tools/acestep
.venv/Scripts/pip install --upgrade ace-step
.venv/Scripts/python cli.py --help  # 测试
```

## 📖 文档

- [架构设计](docs/ARCHITECTURE_V5.md) — V5 架构详解
- [维护指南](docs/MAINTENANCE.md) — 日常维护操作手册
- [视觉提升路线图](docs/VISUAL_ROADMAP.md) — 画面质量提升计划

## 📄 版本历史

| 版本 | 日期 | 主要变化 |
|------|------|----------|
| v5.0 | 2026-06 | YAML 驱动 + Provider 抽象 + 费用追踪 |
| v4.3 | 2026-06 | 工具隔离（独立 venv）+ 质量修复 |
| v4.0 | 2026-05 | 14 步 pipeline + HyperFrames 引擎 |
| v3.0 | 2026-04 | 15 skill 模块化 |

## 📄 License

MIT
