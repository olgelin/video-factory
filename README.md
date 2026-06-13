# 🎬 Video Factory v3

AI驱动的视频自动化生产流水线 — 从话题选择到最终渲染，15个独立skill协同工作。

## 🚀 快速开始

### 环境要求
- Python 3.11+
- FFmpeg
- ImageMagick (用于字幕渲染)
- Git

### 安装
```bash
git clone https://github.com/olgelin/video-factory.git
cd video-factory
pip install -r requirements.txt  # 如有
```

### 配置API
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填入你的API配置
# VF_API_KEY=your-api-key
# VF_BASE_URL=https://api.example.com/v1
# VF_MODEL=your-model-name
```

### 运行Pipeline
```bash
python scripts/orchestrator.py --topic "你的视频话题"
```

## 📁 项目结构

```
video-factory/
├── src/                    # 核心引擎
│   ├── engine.py          # 主引擎 (API调用、重试、降级)
│   └── ...
├── scripts/                # 15个独立skill
│   ├── orchestrator.py    # Pipeline编排器
│   ├── topic_selector.py  # 话题选择
│   ├── script_writer.py   # 剧本生成
│   ├── storyboard.py      # 分镜设计
│   ├── voice_gen.py       # 语音合成
│   ├── bgm_gen.py         # 背景音乐生成
│   ├── design_system.py   # 视觉设计系统
│   ├── hf_builder.py      # HyperFrames HTML构建
│   ├── subtitle_gen.py    # 字幕生成
│   ├── audio_mixer.py     # 音频混合
│   ├── video_renderer.py  # 视频渲染
│   └── ...
├── hf-project/            # HyperFrames视觉引擎
├── assets/                # 静态资源
├── docs/                  # 文档
└── AGENTS.md              # AI Agent协作规范
```

## 🎯 核心特性

- **15个独立skill** — 模块化设计，每个skill可独立运行和测试
- **多LLM支持** — 通过环境变量切换任意OpenAI兼容API
- **自动重试** — 3级渐进重试机制，处理API超时和限流
- **视觉引擎** — 基于HyperFrames的HTML/CSS/GSAP动画渲染
- **完整流水线** — 从话题到成片，全自动化

## 📖 文档

- [Video Factory V3 Plan](VIDEO_FACTORY_V3_PLAN.md) — 架构设计
- [AGENTS.md](AGENTS.md) — AI Agent协作规范
- [docs/](docs/) — 详细文档

## 📄 License

MIT

---

> Built with [Hermes Agent](https://hermes-agent.nousresearch.com)
