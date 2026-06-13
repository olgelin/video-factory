---
name: video-factory
slug: video-factory
version: 3.0.0
description: "15-skill autonomous video production pipeline — topic research → script → voice → BGM → HyperFrames HTML render → final MP4. Powered by Xiaomi MiMo LLM + VoxCPM2 voice clone + ACE-Step music generation."
tags: video, pipeline, automation, short-video, hyperframes, ai-video, tts, bgm, mimo
metadata:
  clawdbot:
    emoji: "🎬"
    requires:
      bins: [python3, ffmpeg, node, npx]
      env: [XIAOMI_API_KEY]
    os: [linux, darwin, win32]
---

# Video Factory — Autonomous Short Video Pipeline

15个独立skill组成的全自动短视频生产线：热点采集 → 话题筛选 → 脚本生成 → 配音 → BGM → HTML渲染 → 视频合成 → 交付。

## When to Use

- 用户要求生成短视频
- 用户提到"视频工厂"、"video factory"、"短视频制作"
- 需要从话题到成品视频的全自动化流程
- 需要单独执行某个pipeline stage（如只生成BGM、只生成脚本）

## Prerequisites

### 必需环境
- Python 3.11+
- FFmpeg（音频/视频处理）
- Node.js 20+（HyperFrames CLI）
- Xiaomi MiMo API Key（`XIAOMI_API_KEY` 环境变量）

### 可选ML依赖（语音+BGM功能需要）
- PyTorch + torchaudio（VoxCPM2语音克隆 + ACE-Step BGM生成）
- faster-whisper（语音转文字）
- soundfile（音频I/O）

### 模型下载
```bash
# VoxCPM2 语音克隆模型
pip install voxcpm_package
# 或从 HuggingFace: openbmb/VoxCPM2

# ACE-Step 1.5 BGM生成模型
pip install acestep_package
# 或从 HuggingFace: ACE-Step/Ace-Step1.5
```

## Quick Start

```bash
# 完整pipeline
python scripts/orchestrator.py --topic "AI替代程序员的真相"

# 跳过耗时步骤（开发调试）
python scripts/orchestrator.py --topic "测试" --skip voice_gen bgm_generator

# 只执行特定步骤
python scripts/orchestrator.py --topic "测试" --only script_writer storyboard

# 列出所有skill
python scripts/orchestrator.py --list
```

## Pipeline Architecture

```
topic_scout → topic_selector → script_writer → lyrics_writer
                                                  ↓
              style_learner ← (parallel)     bgm_generator
                  ↓                                ↓
              design_system                   audio_mixer ← voice_gen ← transcriber
                  ↓                               ↓
              storyboard → hf_builder → video_renderer → packager → final.mp4
                  ↓
              asset_manager
```

### 15 Skills

| # | Skill | 功能 | LLM | ML模型 |
|---|-------|------|-----|--------|
| 1 | topic_scout | 多平台热点采集、去重交叉验证 | — | — |
| 2 | topic_selector | 多维度评分选题 | MiMo | — |
| 3 | script_writer | Ali厂长科技风口播脚本 | MiMo | — |
| 4 | lyrics_writer | 深层映射歌词（副歌开头） | MiMo | — |
| 5 | style_learner | 从样本提炼写作风格 | MiMo | — |
| 6 | design_system | 视觉设计系统（配色/排版/动效） | MiMo | — |
| 7 | voice_gen | 逐段配音+合并+变速 | — | VoxCPM2 |
| 8 | transcriber | 语音转文字+逐词时间戳 | — | faster-whisper |
| 9 | bgm_generator | 歌词→BGM音乐 | — | ACE-Step |
| 10 | storyboard | 分镜创意方向 | MiMo | — |
| 11 | asset_manager | 网页素材下载/截图 | — | — |
| 12 | hf_builder | HyperFrames HTML场景构建 | MiMo | — |
| 13 | video_renderer | HTML→MP4渲染 | — | HyperFrames CLI |
| 14 | audio_mixer | 语音+BGM+视频混音 | — | FFmpeg |
| 15 | packager | 成品封装+交付目录 | — | — |

## Output Structure

```
output/
├── topic_selected.json     # 选题结果
├── step03_script.json      # 口播脚本
├── lyrics.txt              # BGM歌词
├── style_profile.json      # 风格画像
├── design.md               # 设计系统
├── storyboard.json         # 分镜设计
├── step05_voice.wav        # 配音音频
├── whisperx_transcript.json # 逐词时间戳
├── captions.srt            # 字幕文件
├── bgm.wav                 # BGM音乐
├── step10_video.mp4        # 渲染视频
├── step11_final.mp4        # 最终成品
└── final_context.json      # 完整pipeline上下文
```

## Configuration

### 环境变量
```bash
# 必需
XIAOMI_API_KEY=your_mimo_api_key

# 可选（DeepSeek备用）
DEEPSEEK_API_KEY=your_deepseek_key

# 可选（自定义.env路径）
HERMES_HOME=/path/to/hermes
```

### LLM配置
默认使用 Xiaomi MiMo v2.5，支持自动fallback到DeepSeek。在 `scripts/llm_utils.py` 中配置。

### 内容过滤
内置敏感词中和机制：当MiMo因敏感词拒绝时，自动用中性同义词替换后重试。

## Design System

默认风格：Ali厂长科技风
- 分辨率：1920×1080 @ 30fps
- 配色：深色背景 + 渐变流光
- 字体：Inter + Microsoft YaHei
- 动效：GSAP slide-up fade-in + stagger

详见 `references/design-system.md`

## Pitfalls

1. **MiMo reasoning_content**：MiMo的思考过程在 `reasoning_content` 字段而非 `content`，llm_utils.py已处理
2. **音频时长**：BGM不要锁死时长（audio_duration=-1），由audio_mixer自动匹配
3. **Storyboard字段映射**：storyboard输出用 `voiceover_text`，hf-builder需要 `narration`，需转换
4. **内容过滤**：高考、离婚等敏感词会触发MiMo拒绝，内置40+词自动中和
5. **VoxCPM2首次加载**：首次运行需下载模型（~9GB），后续从缓存读取

## File Structure

```
video-factory/
├── SKILL.md                    # 本文件
├── scripts/
│   ├── orchestrator.py         # Pipeline编排器（入口）
│   └── llm_utils.py            # LLM调用工具（MiMo + DeepSeek fallback）
├── skills/                     # 15个独立skill模块
│   ├── topic_scout/impl.py
│   ├── topic_selector/impl.py
│   ├── script_writer/impl.py
│   ├── lyrics_writer/impl.py
│   ├── style_learner/impl.py
│   ├── design_system/impl.py
│   ├── voice_gen/impl.py
│   ├── transcriber/impl.py
│   ├── bgm_generator/impl.py
│   ├── storyboard/impl.py
│   ├── asset_manager/impl.py
│   ├── hf_builder/impl.py
│   ├── video_renderer/impl.py
│   ├── audio_mixer/impl.py
│   └── packager/impl.py
├── references/
│   └── design-system.md        # 视觉设计规范
└── templates/
    ├── render-config.schema.json
    ├── sample-render-config.json
    ├── script.schema.json
    └── storyboard.schema.json
```

## License

MIT
