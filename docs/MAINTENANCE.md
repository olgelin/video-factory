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

### ⚠️ HyperFrames 升级后必查的三坑（2026-08-18 全管道测试发现）

这 3 个 bug 在 HyperFrames 0.7.84 → 0.7.109 升级后暴露，**四个管道（short_video / edu_video / edu_music / speech_to_video）全中**。升级引擎后如果渲染崩、卡住、黑屏，按这个顺序排查：

1. **配音超时** — `tool_runner.py` 里 voxcpm 的 timeout 原为 600s，但 14+ 段配音要 15~20 分钟。已改为 `timeout=1800`。症状：`❌ [tool-runner] voxcpm 超时` 或 `步骤 voice_gen 失败`。

2. **THREE 未内联** — `hf-project/skills/hf_builder/impl.py` 的 `_single_llm_generate`（约 1610 行 `final_html`）原来只内联 GSAP、**不内联 three.min.js**。症状：渲染日志报 `ReferenceError: THREE is not defined` + lint 提示 `missing_three_script`，浏览器崩溃。修法：final_html 的 `<head>` 里 GSAP 脚本后加 `{three_script}`（检测 body 含 `THREE.` 就内联 `_load_three_inline()`）。

3. **缺 data-duration** — 场景根 `<div data-composition-id>` 原来没写时长，HyperFrames 推断不出时长，报 `Composition has zero duration` 渲染失败。修法：根 div 加 `data-duration="{duration}"`。

> 关键教训：THREE 内联逻辑在旧路径 `_auto_fix_html`（约 776 行）里有，但新路径 `_single_llm_generate` 走的是自己包裹的 `final_html`，两处不一致。改的时候要确认**实际被调用的那个函数**，别改错。

### 语音转写：faster-whisper 没装不是 bug

转写阶段主路想用 faster-whisper（听音频识别文字），但 `tools/transcriber` 的 venv 里没装 `faster_whisper`，所以每次都失败 → 自动走 fallback。

**fallback 不是"换个转写模型"，而是直接用配音脚本原文 + 配音真实时长生成字幕**（`impl.py` 的 `_fallback_from_voice_durations`）。因为配音是 VoxCPM TTS 念的脚本原文，照抄原文 = 字幕 100% 准确，**比转写还准**（转写反而可能把同音字猜错）。

结论：**对 TTS 配音，faster-whisper 这条主路是多余的，fallback 是更优解，不用修。** 只有将来接入真人录音素材时才需要装 faster-whisper 做真转写。

### Video2X 高清放大失败（exit=3221225477）

`realesr-animevideov3` 模型在 RTX 4060 Ti 上偶发内存访问冲突崩溃。vf 有 fallback：**跳过高清修复、直接用原始视频**，成品不受影响。这不是 vf 的问题，是 Video2X 的 GPU 兼容性。若长期不需要 2x 放大，可跳过该步骤。

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
