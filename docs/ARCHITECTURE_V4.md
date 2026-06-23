# Video Factory V4 架构设计

## 一、现状问题

### 1.1 环境耦合
所有ML工具挤在同一个 core/venv：
- VoxCPM2、ACE-Step、faster-whisper、torch 全部共享
- ace-step 要求 transformers<4.58，锁死了 transformers 版本
- whisperx 要求 torch~=2.8.0，与 torch 2.12 冲突
- 任何工具升级都可能炸其他工具

### 1.2 质量瓶颈
- design_system specs=0（LLM没有生成设计规范）
- hf_builder 依赖LLM生成HTML，质量不稳定
- 没有真实素材（截图、录屏、图标），全靠CSS动画
- 场景切换生硬，没有转场
- BGM和配音节奏不匹配

### 1.3 架构问题
- pipeline是"硬编码串行"，添加新工具要改main_full.py
- 每个skill直接import ML库，无法隔离
- 没有统一的工具调用接口

---

## 二、V4 架构：工具隔离 + 质量升级

### 2.1 核心原则

```
每个工具 = 独立目录 + 独立venv + CLI接口
pipeline主程序 = 轻量编排器，只通过subprocess调用工具
工具之间 = 零依赖，只通过文件交换数据
```

### 2.2 目录结构

```
video-factory/
├── .venv/                          ← pipeline主环境（轻量：llm_utils + 基础库）
├── tools/                          ← 工具隔离层
│   ├── voxcpm/
│   │   ├── .venv/                  ← 独立环境：torch + voxcpm
│   │   ├── requirements.txt
│   │   ├── cli.py                  ← 统一CLI接口
│   │   └── README.md
│   ├── acestep/
│   │   ├── .venv/                  ← 独立环境：torch + acestep + transformers<4.58
│   │   ├── requirements.txt
│   │   ├── cli.py
│   │   └── README.md
│   ├── transcriber/
│   │   ├── .venv/                  ← 独立环境：faster-whisper 或 funasr
│   │   ├── requirements.txt
│   │   ├── cli.py
│   │   └── README.md
│   └── hyperframes/                ← npm生态，已天然隔离
│       └── (全局npm install)
├── skills/                         ← pipeline skills（纯逻辑，不import ML库）
│   ├── topic_scout/
│   ├── topic_selector/
│   ├── script_writer/
│   ├── lyrics_writer/
│   ├── voice_gen/                  ← 通过 subprocess 调用 tools/voxcpm/cli.py
│   ├── design_system/
│   ├── transcriber/                ← 通过 subprocess 调用 tools/transcriber/cli.py
│   ├── bgm_generator/              ← 通过 subprocess 调用 tools/acestep/cli.py
│   ├── storyboard/
│   ├── hf_builder/
│   ├── video_renderer/             ← 通过 subprocess 调用 hyperframes CLI
│   └── audio_mixer/                ← 通过 subprocess 调用 ffmpeg
├── hf-project/                     ← HyperFrames项目（渲染产物）
├── output/                         ← pipeline输出
├── main_v4.py                      ← 新pipeline编排器
└── core/                           ← 基础设施（resource_checker, metrics等）
```

### 2.3 工具CLI接口规范

每个工具的 cli.py 统一接口：

```python
# tools/voxcpm/cli.py
"""
用法: python cli.py --input script.json --output voice.wav [--speed 1.2]
"""
import argparse, json, sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    from voxcpm import VoxCPM
    model = VoxCPM.from_pretrained(MODEL_PATH)

    with open(args.input) as f:
        script = json.load(f)

    audio = model.generate(script["text"], speed=args.speed)

    import soundfile as sf
    sf.write(args.output, audio, SAMPLE_RATE)
    print(json.dumps({"duration": len(audio)/SAMPLE_RATE, "path": args.output}))
```

### 2.4 Pipeline调用方式

```python
# skills/voice_gen/impl.py（V4版本）
import subprocess, json

def run(context):
    script_path = context["script_path"]
    output_path = str(OUTPUT_DIR / "step05_voice.wav")

    result = subprocess.run(
        ["tools/voxcpm/.venv/Scripts/python.exe", "tools/voxcpm/cli.py",
         "--input", script_path, "--output", output_path, "--speed", "1.2"],
        capture_output=True, text=True, timeout=300, cwd=str(WORKSPACE)
    )

    if result.returncode != 0:
        raise RuntimeError(f"VoxCPM2失败: {result.stderr}")

    metadata = json.loads(result.stdout)
    context["voice_path"] = output_path
    context["voice_duration"] = metadata["duration"]
    return context
```

---

## 三、质量升级策略

### 3.1 视觉质量（hf_builder）

**问题**：LLM生成的HTML质量不稳定，design_system specs=0

**解决方案**：

1. **强制design_system输出specs**
   - 设计规范必须包含：配色方案、字体栈、间距系统、动画库
   - LLM必须输出JSON格式的design_specs.json
   - 验证：specs数量>=5，否则重试

2. **场景模板库**（已有templates/，需扩充）
   - 数据展示模板：数字冲击、对比图表、趋势线
   - 故事叙述模板：时间线、流程图、因果链
   - 情感渲染模板：警示灯、爆炸效果、心跳线
   - 每个模板 = HTML + GSAP动画 + 配色适配接口

3. **真实素材注入**
   - 截图/录屏：通过浏览器自动化获取
   - 图标：使用SVG图标库（不依赖外部CDN）
   - 背景：动态渐变 + 粒子效果（CSS/GSAP）

4. **场景转场**
   - HyperFrames支持transition配置
   - 添加：淡入淡出、滑动、缩放、粒子过渡
   - 转场时长0.5-1s，不打断内容节奏

### 3.2 音频质量（voice_gen + bgm_generator）

**问题**：BGM和配音节奏不匹配

**解决方案**：

1. **BGM节奏适配**
   - 根据配音语速（字/分钟）选择BPM
   - 快节奏配音 -> 高BPM BGM
   - 沉稳配音 -> 低BPM BGM
   - 在ACE-Step prompt中注入BPM参数

2. **音量动态混合**
   - 配音段落：BGM降低到-12dB
   - 转场段落：BGM恢复到-6dB
   - 重点强调：BGM + 音效叠加

3. **音效层**
   - 数据冲击：低音boom
   - 转场：whoosh
   - 强调：叮咚/叮
   - 通过FFmpeg混合到BGM轨道

### 3.3 内容质量（script_writer + storyboard）

**问题**：选题结构决定80%质量（6/20教训）

**解决方案**：

1. **选题结构预判**
   - topic_selector输出时评估"视频化潜力"
   - 有天然子话题的选题（消费/投资/债务）-> 高分
   - 开放式问题 -> 低分，需要重新聚焦

2. **剧本结构模板**
   - 三盏红灯结构（问题->证据->解决方案）
   - 数据冲击结构（数字->对比->趋势->预测）
   - 故事弧线结构（背景->冲突->高潮->结局）
   - LLM根据选题类型自动选择结构

3. **分镜精确化**
   - 每个场景必须有：视觉概念、动画描述、数据来源
   - 不能只有"展示数据"，必须指定"数字从0跳到15万，伴随红色脉冲"
   - storyboard输出必须包含GSAP动画指令

---

## 四、实施计划

### Phase 1：工具隔离（1天）
1. 创建 tools/ 目录结构
2. 为每个ML工具创建独立venv + requirements.txt + cli.py
3. 修改voice_gen/bgm_generator/transcriber使用subprocess调用
4. 验证：每个工具独立运行成功

### Phase 2：质量升级 - 视觉（1天）
1. 修复design_system强制输出specs
2. 扩充场景模板库（10+模板）
3. 添加场景转场效果
4. 验证：hf_builder输出质量提升

### Phase 3：质量升级 - 音频（0.5天）
1. BGM节奏适配（BPM匹配）
2. 音量动态混合
3. 音效层添加
4. 验证：音频混合质量提升

### Phase 4：质量升级 - 内容（0.5天）
1. 选题结构预判
2. 剧本结构模板
3. 分镜精确化
4. 验证：内容质量提升

### Phase 5：端到端验证（0.5天）
1. 完整pipeline运行
2. 对比V3 vs V4视频质量
3. 修复遗留问题
4. 文档更新

---

## 五、数据流图（V4）

```
                    Pipeline 主编排器 (main_v4.py)
                    轻量环境：llm_utils + 基础库
                                |
          +---------------------+---------------------+
          |                     |                     |
     Phase 1               Phase 2               Phase 3
     选题+剧本             并行生成               渲染+混合
          |                     |                     |
    +-----+-----+        +------+------+        +----+----+
    |     |     |        |      |      |        |    |    |
    v     v     v        v      v      v        v    v    v
  scout select script  voice  lyrics design   build render mix
  (LLM) (LLM) (LLM)  |      (LLM)  (LLM)   (LLM) (HF) (FFmpeg)
                       |                           ^
                +------+------+                    |
                | tools/voxcpm |                    |
                | .venv/cli.py |                    |
                +--------------+                    |
                                                    |
                +--------------+         +----------+
                | tools/ace    |         |
                | .venv/cli.py |         |
                +------+-------+         |
                       |                 |
                       v                 |
                    bgm_gen              |
                       |                 |
                       v                 |
                +--------------+         |
                | tools/trans  |         |
                | .venv/cli.py |         |
                +------+-------+         |
                       |                 |
                       v                 |
                   transcriber ---------+
                       |
                       v
                   storyboard
```

### 文件交换协议

| 阶段 | 输出文件 | 格式 | 下游消费者 |
|------|----------|------|-----------|
| topic_scout | topic_research.json | JSON | topic_selector |
| topic_selector | topic_selected.json | JSON | script_writer, lyrics_writer |
| script_writer | step03_script.json | JSON | voice_gen, lyrics_writer, storyboard |
| lyrics_writer | lyrics.txt | 纯文本(ACE-Step格式) | bgm_generator |
| voice_gen | step05_voice.wav | WAV | transcriber, audio_mixer |
| design_system | design.md + design_specs.json | MD+JSON | hf_builder, storyboard |
| transcriber | whisperx_transcript.json + captions.srt | JSON+SRT | storyboard, audio_mixer |
| bgm_generator | bgm.wav | WAV | audio_mixer |
| storyboard | storyboard.json | JSON | hf_builder |
| hf_builder | compositions/*.html | HTML | video_renderer |
| video_renderer | step11_final.mp4 | MP4 | audio_mixer |
| audio_mixer | final_output.mp4 | MP4 | packager |
