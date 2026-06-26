# Video Factory V5 架构设计

## 一、架构演进

```
V1-V2:  单体脚本（main.py 几百行）
V3:     15 个独立 skill，但仍硬编码在 main_full.py
V4:     工具隔离（ACE-Step/VoxCPM/Transcriber 各自独立 venv）
V5:     YAML 驱动 + Provider 抽象 + 费用追踪（当前版本）
```

## 二、核心设计原则

### 关注点分离

```
pipeline_defs/short_video.yaml  →  描述"做什么"（步骤顺序、依赖、并行策略）
pipeline_loader.py              →  负责"怎么执行"（加载 YAML、调度、重试）
hf-project/provider.py          →  负责"用哪个模型"（自动发现、评分、路由）
hf-project/cost_tracker.py      →  负责"花了多少钱"（估算、结算、日志）
hf-project/skills/*/impl.py     →  负责"具体怎么做"（每个步骤的实现）
```

### 工具隔离（V4 遗产）

```
tools/
├── acestep/.venv/     ← 独立 Python 环境（torch + ace-step + transformers<4.58）
├── voxcpm/.venv/      ← 独立 Python 环境（torch + voxcpm）
├── transcriber/.venv/ ← 独立 Python 环境（faster-whisper 或 funasr）
└── video2x/           ← 独立 exe，天然隔离
```

每个工具通过 `subprocess` 调用 `cli.py`，主 pipeline 不 import 任何 ML 库。
升级一个工具不会炸其他工具。

## 三、Pipeline 执行模型

### Phase 分组

```
Phase 1 (串行):
  topic_scout → topic_selector → script_writer

Phase 2 (并行, group_a):
  lyrics_writer + voice_gen + design_system

Phase 3 (并行, group_b):
  transcriber + bgm_generator

Phase 3.5 (串行):
  storyboard (依赖 Phase 3 产出)

Phase 4 (串行):
  hf_builder → video_renderer → video_upscaler → audio_mixer
```

### 执行规则

- 同一 Phase 内、同一 `parallel_group` 的步骤并行执行
- 不同 `parallel_group` 之间串行
- 不同 Phase 之间串行
- `critical: true` 的步骤失败则终止 pipeline
- `retry: N` 的步骤失败后自动重试 N 次

## 四、LLM Provider 架构

### 自动发现

从 `E:\Hermes-Agent\config.yaml` 读取 `model.default` 字段，自动解析所有模型：

```yaml
model:
  default: deepseek-v4-pro,deepseek-v4-flash,kimi-k2.7-code,glm-5.2,minimax-m3
  provider: custom
  base_url: https://ark.cn-beijing.volces.com/api/plan/v3
  api_key: ark-...
```

同时读取 `auxiliary.*` 下的辅助模型（approval/title/vision）。

### 智能路由

按任务类型选最优模型：

| 任务类型 | 偏好 | 适用步骤 |
|----------|------|----------|
| research | 快+便宜 | topic_scout |
| selection | 均衡 | topic_selector |
| creative | 质量+创意 | script_writer, hf_builder, design_system, storyboard, lyrics_writer |
| analysis | 快+准 | 质量诊断 |

### 7 维评分

```
task_fit × 0.30 + output_quality × 0.20 + control × 0.15
+ reliability × 0.15 + cost_efficiency × 0.10
+ latency × 0.05 + continuity × 0.05
```

### 限流保护

令牌桶：每 60 秒最多 10 次调用。超限自动等待。429 响应自动重试 3 次。

## 五、数据流

```
topic_scout          → output/topic_research.json
topic_selector       → output/topic_selected.json
script_writer        → output/step03_script.json
lyrics_writer        → output/lyrics.txt
voice_gen            → output/step05_voice.wav
transcriber          → output/whisperx_transcript.json + captions.srt
bgm_generator        → output/bgm.wav
design_system        → output/design.md + design_specs.json
storyboard           → output/storyboard.json
hf_builder           → hf_render_project/compositions/beat-*.html
video_renderer       → output/step10_video.mp4
video_upscaler       → output/step13_upscaled.mp4
audio_mixer          → output/step11_final.mp4  ← 最终产物
```

所有中间产物保存在 `hf-project/output/`，支持断点续跑（`--steps N-M`）。

## 六、关键文件

| 文件 | 作用 | 修改频率 |
|------|------|----------|
| `pipeline_defs/short_video.yaml` | Pipeline 定义 | 加步骤时改 |
| `pipeline_loader.py` | 执行引擎 | 几乎不改 |
| `hf-project/provider.py` | LLM 路由 | 换模型时可能改 |
| `hf-project/cost_tracker.py` | 费用追踪 | 几乎不改 |
| `hf-project/llm_utils.py` | 向后兼容层 | 不改 |
| `hf-project/skills/*/impl.py` | 各步骤实现 | 优化步骤时改 |
| `run.py` | 入口 | 几乎不改 |
| `E:\Hermes-Agent\config.yaml` | 模型配置 | 换模型时改 |
