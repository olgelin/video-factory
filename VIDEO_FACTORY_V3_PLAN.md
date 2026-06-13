# 视频工厂 v3.0 执行计划

> **状态**：已对齐，准备执行
> **核心理念**：HyperFrames = 执行机器，不是灵感机器。先准备好所有文件，再让Agent构建。
> **来源**：博主Ali厂长的HyperFrames正确使用教程 + HyperFrames官方6步流程

---

## 一、完整Skill清单（14个）

| Phase | # | Skill | 核心问题 | 输入 | 输出 | 状态 |
|---|---|---|---|---|---|---|
| 2 | 1 | **topic-scout** | 选题采集+信息源截屏/录屏 | 关键词/热点源 | topics.json + assets/sources/ 截图录屏 | 待建 |
| 1 | 2 | **design-system** | 视觉风格定义 | 用户选择 | design.md（含片头片尾模板） | 已有 |
| 2 | 3 | **script-writer** | 口播稿创作 | topics.json | script.md（纯文本） | 待建 |
| 2 | 4 | **storyboard** | 分镜设计 | script.md + design.md | storyboard.md | 待建 |
| 1 | 5 | **voice-generator** | 配音生成 | script.md | narration.wav | 已有VoxCPM2 |
| 1 | 6 | **transcriber** | 逐词时间戳 | narration.wav | transcript.json | 已有faster-whisper |
| 2 | 7 | **lyrics-writer** | 歌词创作 | script.md + mood | lyrics.txt（ACE-Step格式） | 待建 |
| 2 | 8 | **bgm-generator** | BGM（带人声） | lyrics.txt + caption | bgm.wav | 待建 |
| 2 | 9 | **asset-manager** | 素材管理 | topic-scout采集 + storyboard需求 | assets/ 标准目录 | 待建 |
| **1** | **10** | **hf-builder** | **核心：读所有文件→写HTML** | design.md+script.md+storyboard.md+narration.wav+transcript.json+assets/ | compositions/ + index.html | **Phase 1核心** |
| 1 | 11 | **hf-quality** | 预览校验渲染 | index.html | raw_video.mp4 + QA报告 | 待建 |
| 3 | 12 | **audio-mixer** | 音频混合 | narration.wav + bgm.wav | mixed.wav | 待建 |
| 3 | 13 | **video-upscaler** | 高清修复 | raw_video.mp4 | hd_video.mp4 | 待建 |
| 3 | 14 | **packager** | 封装交付 | hd_video.mp4 + mixed.wav | deliverables/ + 封面截图 | 待建 |

---

## 二、每个Skill详细设计

### 1. topic-scout — 选题采集+信息源采集

**核心职责**：找到好选题 + 采集信息源的截图/录屏作为素材

**功能**：
1. 搜索热点/趋势（抖音热搜、百度热搜、微博等）
2. 筛选可操作的选题
3. **采集信息源**：浏览器打开信息源页面 → 截屏/录屏 → 存入 assets/sources/
4. 输出 topics.json

**输入**：关键词、热点源配置

**输出**：
```
output/
├── topics.json              # 选题结果
assets/
└── sources/                 # 信息源截图/录屏
    ├── source_01.png        # 截图：股市跌停页面
    ├── source_02.png        # 截图：相关新闻
    └── source_03.mp4        # 录屏：浏览器操作过程
```

**topics.json 格式**：
```json
{
  "selected_topic": {
    "title": "股市跌停潮来了",
    "angle": "散户该怎么应对",
    "source": "东方财富网",
    "reason": "热度高+受众广",
    "source_assets": [
      "assets/sources/source_01.png",
      "assets/sources/source_02.png"
    ]
  }
}
```

**实现要点**：
- 浏览器截图：用 Hermes browser tools (CDP)
- 录屏：用 ffmpeg 或 OBS CLI
- 截图命名要有意义（source_描述.png）

---

### 2. design-system — 视觉风格定义

**已确认**：用户提供的Ali厂长复刻版design.md

**关键内容**：
- 颜色系统：橙#FF7A2E / 蓝#00B4FF / 紫#A855F7 / 绿#10B981 / 黄#FBBF24
- 排版：标题80px/副标题32px/卡片标题36px/正文24px
- 组件：发光卡片/六宫格/步骤流/六边形时间线/列表项/警告框
- 动画：上滑淡入0.6s / 逐个0.15s延迟 / 脉冲3s循环
- 片头：品牌logo动画（3秒）
- 片尾："不闻AI" + 关注引导（5秒）

---

### 3. script-writer — 口播稿创作

**输入**：topics.json
**输出**：script.md（纯文本，不是JSON）

**script.md 格式**：
```
# 口播稿 - 股市跌停潮来了

嘿各位，今天A股直接崩了，跌停板排成队，你慌不慌？

但我要告诉你，真正的老手这时候反而在捡便宜货。

数据不会骗人，今天跌停超过200家，但北向资金逆势流入了50亿。

具体怎么操作？三个建议，第一不要恐慌割肉，第二关注被错杀的优质股，第三设好止损线。

记住，市场永远是反人性的，别人恐惧的时候你要贪婪。

关注我，下期教你怎么在暴跌中找到翻倍股。
```

**格式要求**：
- 每段口播之间空一行
- 口语化、有节奏感
- 400-600字
- 开头要hook，结尾要CTA

---

### 4. storyboard — 分镜设计

**输入**：script.md + design.md
**输出**：storyboard.md

**storyboard.md 格式**：
```
# 分镜脚本 - 股市跌停潮来了

## Scene 1 (0.0s - 6.5s)
- **配音**: 嘿各位，今天A股直接崩了，跌停板排成队，你慌不慌？
- **视觉类型**: quote_hero
- **画面**: 大标题"A股跌停潮"渐变文字(紫白)，橙色发光边框
- **动画**: 标题SLAMS从左入场，副标题CASCADE
- **素材**: 无（纯CSS场景）
- **字幕**: 底部黄色字幕条

## Scene 2 (6.5s - 15.0s)
- **配音**: 但我要告诉你，真正的老手这时候反而在捡便宜货。
- **视觉类型**: data_impact
- **画面**: 大数字"200+"跌停家数 + 对比卡"北向资金+50亿"
- **动画**: 数字COUNTS UP，卡片逐个上滑
- **素材**: assets/sources/source_01.png（股市截图）
- **字幕**: 底部黄色字幕条

## Scene 3 (15.0s - 28.0s)
- **配音**: 具体怎么操作？三个建议...
- **视觉类型**: list_alert（六宫格变体）
- **画面**: 3个建议卡片（橙/蓝/绿色），虚线边框
- **动画**: 卡片逐个从下滑入，延迟0.15s
- **素材**: 无
- **字幕**: 底部黄色字幕条

## Scene 4 (28.0s - 35.0s)
- **配音**: 记住，市场永远是反人性的...
- **视觉类型**: quote_hero
- **画面**: 金句大字 + 背景氛围光
- **动画**: FADE IN
- **素材**: 无

## Scene 5 (35.0s - 40.0s) — 片尾
- **配音**: 关注我，下期教你怎么在暴跌中找到翻倍股。
- **视觉类型**: 结尾模板（design.md定义）
- **画面**: "不闻AI" + 关注引导 + logo
- **动画**: 固定模板动画
```

**格式要求**：
- 每个Scene包含：配音/视觉类型/画面/动画/素材/字幕
- 素材路径必须指向实际文件
- 视觉类型必须是HyperFrames支持的类型
- 时间戳基于配音时长估算（transcriber精确化后更新）

---

### 5. voice-generator — 配音生成

**已有**：VoxCPM2

**接口**：
- 输入：script.md → 提取纯文本
- 输出：output/narration.wav（WAV格式，24kHz）

---

### 6. transcriber — 逐词时间戳

**方案**：faster-whisper（纯本地，CPU可用）

**接口**：
- 输入：output/narration.wav
- 输出：output/transcript.json

**transcript.json 格式**：
```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 6.5,
      "text": "嘿各位今天A股直接崩了跌停板排成队你慌不慌",
      "words": [
        {"word": "嘿", "start": 0.0, "end": 0.3},
        {"word": "各位", "start": 0.3, "end": 0.8},
        {"word": "今天", "start": 0.9, "end": 1.3},
        {"word": "A股", "start": 1.4, "end": 1.8}
      ]
    }
  ]
}
```

---

### 7. lyrics-writer — 歌词创作

**输入**：script.md + mood
**输出**：output/lyrics.txt（ACE-Step 1.5格式）

**lyrics.txt 格式**：
```
[Chorus]
燃烧的数字跳动着
红色的海洋吞没一切
谁在恐惧中站稳脚跟

[Verse 1]
屏幕上的曲线向下坠落
每个数字都是一声叹息

[Chorus]
燃烧的数字跳动着
红色的海洋吞没一切
谁在恐惧中站稳脚跟

[Bridge - whispered]
但真正的勇者在废墟中捡起黄金

[Outro - fade out]
别怕 有我在
```

**创作要求**：
- 副歌开头（[Chorus]在最前面）
- 独立创作的氛围歌词（不是口播内容的复述）
- 融入情感，有深度
- 根据口播内容的情绪选择创作风格

---

### 8. bgm-generator — BGM生成

**方案**：ACE-Step 1.5

**接口**：
- 输入：output/lyrics.txt + caption参数
- 输出：output/bgm.wav

**caption示例**：`"pop, emotional, male vocal, piano, 120bpm, catchy melody"`

**BGM时长处理**：
- ACE-Step最长600秒
- 如果BGM < 配音时长 → 循环填充
- 如果BGM > 配音时长 → 裁切
- 处理在audio-mixer中完成

---

### 9. asset-manager — 素材管理

**核心职责**：整理素材到标准目录结构

**输入**：
- topic-scout采集的截图/录屏
- storyboard.md中声明的素材需求
- design.md中的品牌素材（logo等）

**输出**：assets/ 标准目录
```
assets/
├── sources/           # 来自topic-scout的截图/录屏
│   ├── source_01.png
│   └── source_02.mp4
├── icons/             # SVG图标（如有需要）
├── screenshots/       # 产品/网页截图
└── brand/             # 品牌素材（logo等）
```

**关键**：
- 不"制作"素材，只"管理和组织"
- 截图+录屏来自topic-scout
- 大部分视觉效果用CSS实现（发光卡片、渐变文字等不需要外部图片）
- 未来可扩展AI生图

---

### 10. hf-builder — 核心：HTML视频工程构建

**这是整个系统的核心skill。**

**职责**：读取所有输入文件 → 按照HyperFrames官方6步流程 → 生成完整的HTML视频工程

**输入**：
```
project/
├── design.md          # 2. design-system
├── script.md          # 3. script-writer
├── storyboard.md      # 4. storyboard
├── narration.wav      # 5. voice-generator
├── transcript.json    # 6. transcriber
├── bgm.wav            # 8. bgm-generator（可选）
└── assets/            # 9. asset-manager
```

**输出**：
```
project/
└── compositions/
    ├── beat-01.html   # 场景1（sub-composition）
    ├── beat-02.html   # 场景2
    ├── ...
    └── index.html     # 主composition（引用所有beat）
```

**构建流程（HyperFrames官方6步）**：

```
Step 1: 读取design.md → 确定视觉身份
Step 2: 读取storyboard.md + script.md → 理解每个场景的意图
Step 3: 规划结构 → 确定场景数、节奏、转场
Step 4: Layout First → 先写静态HTML+CSS终态
Step 5: Animate → 再加GSAP动画
Step 6: 组装index.html → 引用音频+字幕
```

**关键规则**：
- 遵循HyperFrames SKILL.md中的所有Non-Negotiable规则
- 每个场景是独立的sub-composition（beat-XX.html）
- index.html是主composition，引用所有beat
- 字幕用HyperFrames自带caption组件
- transcript.json驱动逐词高亮
- narration.wav作为音频轨道
- bgm.wav作为背景音乐轨道（可选）
- assets/中的素材通过相对路径引用

---

### 11. hf-quality — 预览校验渲染

**职责**：对hf-builder生成的HTML进行质量检查和渲染

**流程**：
```
1. npx hyperframes lint      → 结构检查
2. npx hyperframes validate   → 验证+对比度
3. npx hyperframes inspect    → 布局检查
4. npx hyperframes render     → 渲染为MP4
```

**输出**：
- output/raw_video.mp4 — 原始渲染视频
- output/qa_report.json — QA报告

---

### 12. audio-mixer — 音频混合

**职责**：混合配音+背景音乐

**接口**：
- 输入：narration.wav + bgm.wav（可选）
- 输出：output/mixed.wav

**处理**：
- 配音为主（音量1.0）
- BGM为辅（音量0.3-0.5）
- BGM循环/裁切适配配音时长
- 响度标准化（-16 LUFS）
- 淡入淡出

---

### 13. video-upscaler — 高清修复

**方案**：Video2X CLI（Windows原生）

**Video2X v6.4.0 CLI**：
- 下载：video2x-6.4.0-windows-amd64-cli.zip
- 内置Real-ESRGAN + Real-CUGAN + RIFE
- Vulkan后端（任何GPU）
- 不需要Python/conda

**接口**：
- 输入：output/raw_video.mp4
- 输出：output/hd_video.mp4

---

### 14. packager — 封装交付

**职责**：
1. 合并音频+视频（ffmpeg）
2. 生成封面（HTML渲染→截图）
3. 添加片头片尾（design.md中的模板）
4. 输出最终交付物

**输出**：
```
deliverables/
├── final.mp4          # 最终视频
├── cover.png          # 封面截图
├── qa_report.json     # QA报告
└── manifest.json      # 打包清单
```

---

## 三、数据接口汇总

### 文件格式一览

| 文件 | 格式 | 说明 |
|---|---|---|
| design.md | Markdown | 视觉风格（颜色/字体/组件/动画/片头片尾） |
| script.md | Markdown | 口播稿（纯文本，每段空行分隔） |
| storyboard.md | Markdown | 分镜（每scene的配音/视觉/画面/动画/素材） |
| narration.wav | WAV | 配音音频（24kHz） |
| transcript.json | JSON | 逐词时间戳 |
| lyrics.txt | 纯文本 | ACE-Step歌词（含结构标签） |
| bgm.wav | WAV | 背景音乐（含人声） |
| assets/ | 目录 | 截图/录屏/图标 |
| compositions/ | 目录 | HyperFrames HTML工程 |

### Skill依赖图

```
topic-scout ──→ script-writer ──→ storyboard ──→ hf-builder ──→ hf-quality ──→ packager
     |              |                |              |              |
     |              v                v              |              v
     |         voice-gen ──→ transcriber ───────────┘         video-upscaler
     |              |
     |              v
     |         lyrics-writer ──→ bgm-generator ──→ audio-mixer ──→ packager
     |
     v
asset-manager ──→ hf-builder
```

---

## 四、执行计划

### Phase 1：打通核心链路（预计3天）

**目标**：用手动准备的文件，让hf-builder生成高质量HTML，渲染出成品视频。

#### Day 1：环境准备 + 输入文件
1. 升级torch到2.6.0 + 测试VoxCPM2兼容性
2. 验证transcriber：用faster-whisper对现有narration.wav转录
3. 手动准备输入文件：design.md + script.md + storyboard.md + transcript.json
4. 下载Video2X CLI + 验证可用

#### Day 2：构建hf-builder skill
1. 加载hyperframes skill，读取所有references
2. 实现hf-builder核心逻辑：读取所有文件 → 生成HTML
3. 遵循HyperFrames官方规则：Layout First → Animate

#### Day 3：渲染 + 视觉QA
1. 运行hf-quality：lint/validate/inspect/render
2. 抽帧视觉QA（vision_analyze检查3-5帧）
3. 用Video2X CLI测试高清修复
4. 最终输出成品视频

**Phase 1验收标准**：
- 视频时长 >= 30秒
- 分辨率 1920x1080
- H.264 + AAC双轨
- 字幕跟随配音时间出现
- 每个场景有入场动画
- 视觉风格与design.md一致
- hyperframes lint 通过
- hyperframes validate 无严重错误

### Phase 2：自动化上游Skill（预计5天）

按顺序构建：
1. script-writer — LLM生成script.md
2. voice-generator — VoxCPM2封装
3. transcriber — faster-whisper封装
4. lyrics-writer — LLM生成lyrics.txt
5. bgm-generator — ACE-Step 1.5封装

### Phase 3：自动化下游 + 打磨（预计4天）

1. asset-manager — 素材整理
2. audio-mixer — ffmpeg混合+循环裁切
3. video-upscaler — Video2X CLI封装
4. packager — 封装+封面+片头片尾
5. topic-scout — 选题+信息源采集

---

## 五、风险应对

| 风险 | 应对 |
|---|---|
| torch升级影响VoxCPM2 | 独立venv隔离 |
| faster-whisper CPU太慢 | 用medium模型（已验证可用） |
| Video2X CLI不兼容 | 用realesrgan-ncnn-vulkan（2MB CLI） |
| ACE-Step模型太大 | 用turbo版 + 5Hz LM（已验证16GB可用） |
| HyperFrames HTML生成质量差 | 参考博主的设计规范，严格遵循HyperFrames规则 |

---

## 六、关键参考文档

- HyperFrames SKILL.md — 官方6步流程+所有规则
- HyperFrames references/beat-direction.md — 节奏规划
- HyperFrames references/captions.md — 字幕组件（15种）
- HyperFrames references/video-composition.md — 视频介质规则
- HyperFrames references/transitions.md — 转场效果
- design.md — 用户提供的Ali厂长复刻版视觉规范
- ClawHub — find-skills查看是否有可复用的技能
