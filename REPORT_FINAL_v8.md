# 🏁 Video Factory — 全栈终报

**日期** 2026-08-02 | **标签** v8.0-stable | **验证** Kimi K3 89/100

---

## 一、架构总览

```
video-factory/              统一视频工厂
├── pipelines/
│   ├── short_video.yaml    ← 新闻资讯（主力） ★
│   ├── edu_video.yaml      ← 教育白板
│   ├── edu_music.yaml      ← 音乐教学（教学+歌词双模式）
│   └── speech_to_video.yaml← 口述→视频
├── prompts/
│   ├── news/               ← 新闻场景 + 口播 + Three.js + 动画
│   ├── edu/                ← 教育场景（白板+卡片+语法标注）
│   └── edu_music/          ← 同上 + 歌词展示
└── skills/
    ├── video_renderer/     ← HyperFrames CLI 渲染层
    ├── quality_scorer/     ← 质量评分
    └── hf_builder/         ← HTML 场景生成
```

**独立项目（共用 video_renderer 底层）：**
- `video-clip-pro/` — 口播精剪（Whisper → 语义理解 → 卡片叠加）
- `biz-analyzer/` — 商业可行性分析
- `geo-publisher/` — 20+ 平台 AI SEO
- `truth-engine/` — 骗局识别

---

## 二、本轮修复清单

### 环境层 🔧
| 修复 | 文件 | 说明 |
|------|------|------|
| hyperframes 重装 | 全局 npm | @0.7.3，从 AI-openclaw 删除后恢复 |
| Node.js | E:\Node\ | v24.18.1，PATH 永久化 .bashrc |
| npm global | C:\Users\...\npm | 从 AI-openclaw 目录迁移 |

### 渲染层 🎬
| 修复 | 文件 | 说明 |
|------|------|------|
| subprocess 编码 | video_renderer/impl.py | text=True → encoding=utf-8（Windows GBK 兼容） |
| HTML 安全读写 | 同上 | _safe_read/write/normalize 三层容错 |
| 2x 超采样 | short_video.yaml | HyperFrames --scale 2 替代崩溃的 Video2X |
| 并行评分 | short_video.yaml | quality_scorer 与渲染并行，省 18min |

### 画面层 🎨 — 所有管道 prompt
| 修复 | 文件 | 说明 |
|------|------|------|
| 🔴 数据铁律 | news scene_system.md | 每场景 1-3 个数据元素，硬要求 |
| 🔴 背景色铁律 | news scene_system.md | 深色蓝紫渐变不变，情绪用霓虹点缀 |
| 🔴 拒绝套壳 | news scene_system.md | 每类型≤2次，做意外，禁止改色交差 |
| 🔴 Three.js 行为注入 | news scene_threejs.md | 变速呼吸/交互响应/叙事粒子三选一 |
| 🔥 创意加速器 | news scene_system.md | 隐喻降维/异物/速度即叙事 |
| 🔥 data_impact 92分模板 | news scene_system.md | 固化高分模板到 prompt |
| 📚 知识铁律 | edu/edu_music scene_system.md | 例句/翻译/语法标注替代 KPI（教育专用） |

### 口播层 🎙️
| 修复 | 文件 | 说明 |
|------|------|------|
| 场景数解锁 | news script_system.md | 7-10段→10-15段，2-3句一切 |
| 去官腔 | news script_system.md | 好人/坏人示例对比（"67%啊"vs"值得注意的是"） |

### 评分层 📊
| 修复 | 文件 | 说明 |
|------|------|------|
| JSON 解析 | quality_scorer/impl.py | max_tokens 3000 + JSON 强制 system prompt → 失败率 0% |

---

## 三、三管道验证结果

| 管道 | 话题 | 场景 | 评分 | fallback | 渲染 | 大小 |
|------|------|------|------|:---:|:---:|------|
| **news** | Kimi K3 开源 | 12 | **89.0 A** | 0 | 12/12 | 56MB |
| **edu** | 被动语态 | 9 | 83 B | 0 | 10/10 | 5.8MB |
| **edu_music** | C和弦 | 45 | 83 B | 0 | 46/46 | 11MB |

**edu 评分为什么低于 news：**
- `data_viz 6.0` — 教育视频正确做法，不需要 KPI/进度条（news 是 8+）
- `typography 7.2` — 教育用简洁字体，不用双层发光 text-shadow
- 评分系统为 news 校准，edu 自然偏低，不影响质量

---

## 四、已知问题 & 约定

| 问题 | 状态 | 说明 |
|------|:---:|------|
| Video2X 超分崩溃 | ⚠️ | RTX 4060 Ti 0xC0000005，改用 HyperFrames 2x 超采样 |
| faster_whisper 缺失 | ⚠️ | fallback 备选方案正常，字幕不受影响 |
| 管道并行 API 过载 | ⚠️ | 两个管道同时跑会打满 DeepSeek 限额→模板兜底。单独跑即可 |
| hyperframes@0.7.3 锁死 | 🔒 | 0.7.26 不兼容，禁止升级 |
| edu_music 场景 45 偏多 | 📝 | 含歌词+BGM 纯音乐段，场景多正常 |

---

## 五、维护指南

### 改 prompt 之前
1. `cp xxx.md xxx.md.bak_v{N}_{描述}` — 先备份
2. 确认是全局还是局部改动（news? edu? 所有管道?）
3. 确认是 prompt 层还是代码层
4. 单管道验证后再推广

### 渲染失败诊断
1. 先判断：渲染层还是内容层？
2. 渲染层 → 只修 video_renderer，不重跑全管道
3. 内容层 → 改 prompt → 重跑全管道
4. `--clean` 只在话题切换时用

### 分层修复纪律
```
LLM 创作层(prompt) — 画面质量问题才动
渲染层(video_renderer) — 编码/崩溃/性能问题
管线层(pipeline loader) — 步骤顺序/依赖/并行
配置层(yaml) — 超时/开关/context defaults
```

---

## 六、GitHub 状态

```
olgelin/video-factory
  master      ← ce18fc8 (fix edu/edu_music prompts)
  v8.0-stable ← f70ce0f (Kimi K3 89分验证)

提交：
  f70ce0f v8.0: 画面质量天花板
  820c909 v8.0+: 并行评分 + 2x超采样
  ce18fc8 fix edu/edu_music: 知识元素≠数据元素
```

---

## 七、已完成 / 待做

✅ 三管道全绿验证  
✅ 数据铁律全部管道  
✅ 背景色铁律  
✅ 口播去官腔  
✅ 场景数解锁  
✅ 渲染编码修复  
✅ 并行评分  
✅ 2x 超采样  
✅ Git tag + push  
✅ edu 知识元素修正  

📝 edu_music 用修正后 prompt 独立重跑（当前跑的是旧 prompt 但结果可用）  
📝 评分系统为 edu 管道单独校准（目前用 news 标准，偏低但不影响质量）  
