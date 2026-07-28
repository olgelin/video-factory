# Video Factory

输入一个话题（或一段口述），自动生成一条完整的短视频（文案 → 配音 → BGM → 画面 → 渲染成品）。

## 它能做什么

Video Factory 是一条全自动视频生产线。支持多种管道：

| 管道 | 触发方式 | 用途 |
|------|---------|------|
| **short_video**（默认） | `python run.py --topic "话题"` | 新闻资讯短视频，自动选题→脚本→画面→成品 |
| **speech_to_video** | `python run.py --speech "口述文本"` | 口语转视频，深度理解口述内容后生成脚本+画面 |
| **edu_video** | `python run.py --pipeline edu_video --topic "话题"` | 教育短视频，白板风格+知识点卡片 |
| **edu_music** | `python run.py --pipeline edu_music --topic "话题"` | 音乐学习视频，教学+歌词展示双模式 |

## 最近更新（2026-07-28）

### 🎮 Three.js 真 3D 渲染
- 所有管道的画面生成支持 Three.js/WebGL 真 3D 元素
- news 管道：5 种 3D 技法（3D 几何背景、GPU 粒子、3D 柱状图、发光环、GLSL Bloom 辉光后期）
- edu 管道：STEM 内容可选 3D 分子/几何模型辅助演示
- edu_music 管道：歌词场景可选 3D 音乐可视化（频谱粒子/光环）
- 通过 HyperFrames（Puppeteer+Chromium）确定性渲染，帧精确无闪烁
- 3D 元素与 CSS 标题/卡片分层叠加，互不干扰

### 🔧 Bug 修复
- letterbox 宽银幕黑边从 108px 缩小到 54px，不再遮挡标题
- film overlay（暗角/颗粒/黑边）注入逻辑修复，不再静默跳过部分场景
- CSS typo 自动修复（`translatex→translateX` 等）
- 片尾话题名传递修复，不再显示"测试"
- speech_processor 升级：从表面清洗升级为深度语义理解+数据补全+情绪拆解

## 安装

```bash
cd video-factory
pip install -r requirements.txt

# 外部工具（需要单独安装）
# - Node.js 22+（HyperFrames 渲染）
# - FFmpeg（音视频处理）
```

## 运行

```bash
# 新闻短视频（自动选题）
python run.py --topic "话题"

# 口语转视频
python run.py --speech "你的口述内容..."

# 教育视频
python run.py --pipeline edu_video --topic "知识点"

# 只跑渲染步骤（前面产物已有）
python run.py --topic "话题" --steps 10-13

# 列出所有可用管道
python run.py --list
```

## 你会得到什么

在 `hf-project/output/` 目录下：

- `step11_final.mp4` — 最终成品视频（带配音、BGM、字幕、画面）
- `step10_video.mp4` — 纯画面（无字幕版本）
- `step05_voice.wav` — AI 配音音频
- `bgm.wav` — 背景音乐
- `captions.srt` — 字幕文件
- `pipeline_context.json` — 完整管线上下文
- `cost_log.json` — API 费用明细

## 项目结构

```
video-factory/
├── run.py                 ← 入口
├── pipeline_loader.py     ← YAML 驱动执行引擎
├── pipeline_defs/         ← 管道 YAML 定义（4 套）
├── hf-project/
│   ├── prompts/           ← LLM 提示词（news/edu/edu_music）
│   ├── skills/            ← 独立模块
│   └── output/            ← 所有产物
├── tools/                 ← 本地工具
└── skills/                ← 自定义 skill（speech_processor 等）
```
