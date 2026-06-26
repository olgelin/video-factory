# Video Factory 维护指南

## 日常使用

### 跑一条视频

```bash
cd E:\Hermes-Agent\workspace\xiaoshan\video-factory

# 完整流程（自动选题）
python run.py

# 指定话题
python run.py --topic "你的话题"

# 只跑部分步骤（断点续跑）
python run.py --topic "你的话题" --steps 10-12

# 竖屏
python run.py --topic "你的话题" --vertical

# 跳过配音/BGM
python run.py --topic "你的话题" --skip-voice --skip-bgm
```

### 查看产物

```
hf-project/output/
├── step11_final.mp4       ← 最终视频
├── step10_video.mp4       ← 无声视频
├── step05_voice.wav       ← 配音
├── bgm.wav                ← 背景音乐
├── cost_log.json          ← 费用记录
└── pipeline_context.json  ← 运行上下文
```

## 换模型

编辑 `E:\Hermes-Agent\config.yaml`：

```yaml
model:
  default: deepseek-v4-pro,deepseek-v4-flash,glm-5.2,minimax-m3
```

Pipeline 自动发现新模型，无需改代码。重启 Hermes Agent 后生效。

## 加新步骤

### 1. 写 skill

在 `hf-project/skills/` 下创建目录和 `impl.py`：

```python
# hf-project/skills/my_step/impl.py
def run(context: dict) -> dict:
    # 从 context 读取输入
    topic = context.get("topic", "")
    # 做你的事
    # ...
    # 返回更新后的 context
    context["my_output"] = "result"
    return context
```

### 2. 注册到 pipeline

在 `pipeline_defs/short_video.yaml` 加一段：

```yaml
  - name: my_step
    step: 14
    skill: my_step
    phase: 4
    parallel_group: null
    description: "我的新步骤"
    input:
      - output/step11_final.mp4
    produces:
      - output/step14_result.mp4
    provider: local
    timeout: 300
    retry: 1
```

不需要改任何 Python 代码。

## 升级本地工具

### ACE-Step 1.5（BGM 生成）

```bash
cd tools/acestep
# 查看当前版本
.venv/Scripts/pip show ace-step

# 升级
.venv/Scripts/pip install --upgrade ace-step

# 测试
.venv/Scripts/python cli.py --help

# 锁定版本
.venv/Scripts/pip freeze > requirements.txt
```

### VoxCPM2（配音）

```bash
cd tools/voxcpm
.venv/Scripts/pip install --upgrade voxcpm
.venv/Scripts/python cli.py --help
.venv/Scripts/pip freeze > requirements.txt
```

### FunASR / Transcriber（语音转录）

```bash
cd tools/transcriber
.venv/Scripts/pip install --upgrade funasr
.venv/Scripts/python cli.py --help
.venv/Scripts/pip freeze > requirements.txt
```

### Video2X（高清修复）

Video2X 是独立 exe，去 [GitHub Releases](https://github.com/k4yt3x/video2x/releases) 下载新版替换 `tools/video2x/video2x.exe`。

## 故障排查

### "No module named 'yaml'"

```bash
# 装到 core venv（不会被 run.py 过滤）
E:\Hermes-Agent\core\venv\Scripts\python.exe -m pip install pyyaml
```

### LLM 调用失败 / 429

- 火山引擎有账号级限流，pipeline 已内置令牌桶 + 重试
- 如果持续 429，减少并发步骤或换模型
- 检查 `E:\Hermes-Agent\config.yaml` 的 api_key 是否过期

### 渲染失败

- 检查 `hf-project/output/cost_log.json` 看哪步失败
- 用 `--steps N-M` 断点续跑
- HyperFrames 渲染失败通常是 HTML 语法问题，看 `video_renderer` 日志

### 配音/BGM 工具报错

- 确认工具 venv 存在：`ls tools/acestep/.venv/`
- 如果 venv 损坏，删除重建：
  ```bash
  cd tools/acestep
  rm -rf .venv
  python -m venv .venv
  .venv/Scripts/pip install -r requirements.txt
  ```

## Git 版本管理

```bash
cd E:\Hermes-Agent\workspace\xiaoshan\video-factory

# 查看历史
git log --oneline -20

# 提交改动
git add -A
git commit -m "描述你的改动"

# 打版本标签
git tag v5.1
git push origin main --tags
```

## 定期检查清单

- [ ] 火山引擎 API Key 是否有效
- [ ] 本地工具（ACE-Step/VoxCPM/Transcriber）是否正常运行
- [ ] GitHub 上这些工具是否有新版本
- [ ] `cost_log.json` 费用是否在预算内
- [ ] 最近产出的视频质量是否满意
