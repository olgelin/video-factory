# CURRENT.md — video-factory 当前状态

> 本文件是 video-factory 的事实源入口。新线程先读本文件，再读 README / docs / knowledge。

## 定位

视频工厂：一条命令自动生成短视频。4 条管线同级 —— short_video（新闻解说）/ edu_video（教育科普）/ edu_music（教学+歌词）/ speech_to_video（口述转视频）。

## 当前版本

- **生产基线：v17**（创意加速器 12 行 + 背景松绑"≥3 项自选"）。v19（Three.js 重写 + 情绪色板）因画面质量下降被否决回滚，**不要回退到 v19 思路**。
- **HyperFrames：0.7.109**（2026-08-16 升级，渲染提速 ~10 倍，已全测通过）
- **最近提交**：`6b94c97`（2026-08-18，0.7.109 升级适配 + 6 管道全测修复）

## 当前状态

- ✅ **活跃，6 条管道全部通过**（vcp pip/fullscreen + vf 四管线），成品均 yuv420p 可播放。
- 入口：`run.py --pipeline <name>`（非 main_full.py）

## 入口索引

| 文件 | 用途 |
|------|------|
| `README.md` | 项目概述 |
| `AGENTS.md` | 干活前必读的知识库加载指引 |
| `docs/MAINTENANCE.md` | 维护指南 + 故障排查（含 0.7.109 三坑） |
| `docs/ARCHITECTURE_V5.md` | 管线执行模型 |
| `knowledge/README.md` | 三级知识库（constraints / bug-patterns / prompt-rules） |
| `knowledge/bug-patterns/` | 缺陷→根因→修复链（改前先查） |

## 已知遗留（非阻塞）

1. **Video2X 上采样崩溃**（exit=3221225477）：RTX 4060 Ti 上 `realesr-animevideov3` 偶发崩溃，管线有 fallback 用原始视频，成品不受影响。
2. **faster_whisper 未装**：**不是问题**。字幕走 fallback（配音脚本原文 + TTS 真实时长），比转写更准。

## 下一步

- **量产验证**：连跑 3-5 个不同话题，测稳定性 + 单条成本 + 良品率（为批量生产铺路）。
- 渲染提速（`video_renderer --workers N`）：受显存限制，暂不动，稳定优先。
