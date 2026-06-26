# Video Factory V5 — Agent Rules

## 项目概述
13 步全自动短视频生产线，YAML 驱动 + Provider 抽象 + 费用追踪。

## 架构原则

### 关注点分离
- `pipeline_defs/short_video.yaml` → 描述"做什么"（改流程改这里）
- `pipeline_loader.py` → 负责"怎么执行"
- `hf-project/provider.py` → 负责"用哪个模型"（自动发现+智能路由）
- `hf-project/cost_tracker.py` → 负责"花了多少钱"
- `hf-project/skills/*/impl.py` → 负责"具体怎么做"

### 工具隔离
ACE-Step/VoxCPM/Transcriber 各自独立 venv，通过 subprocess 调用 cli.py。
升级一个工具不会炸其他工具。

## 编码规范
- Python 3.11+，不锁死任何 LLM provider
- 配置从 `E:\Hermes-Agent\config.yaml` 自动读取
- API Key 绝不硬编码，绝不提交到 git
- 每个 skill 的 impl.py 必须可独立运行

## 关键文件

| 文件 | 修改频率 | 说明 |
|------|----------|------|
| `pipeline_defs/short_video.yaml` | 加步骤时 | Pipeline 定义 |
| `hf-project/provider.py` | 换模型时 | LLM 路由 |
| `hf-project/skills/*/impl.py` | 优化步骤时 | 各步骤实现 |
| `run.py` | 几乎不改 | 入口 |
| `pipeline_loader.py` | 几乎不改 | 执行引擎 |

## 常见坑
- 火山引擎有账号级限流（429），provider.py 已内置令牌桶+重试
- pyyaml 要装到 core venv（`E:\Hermes-Agent\core\venv\`），不是 hermes-agent venv
- hf_builder 连续 LLM 调用有 rate_limit 保护（每次间隔 5s）
- video_renderer 的 outro 场景可能渲染失败（Set maximum size exceeded），非关键可跳过
- 旧 `main_full.py` 保留兼容，新功能走 `run.py`
