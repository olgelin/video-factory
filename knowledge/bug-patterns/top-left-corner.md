# 左上角（画面仅占左上角）

## 症状

视频画面内容集中在左上角，没有占满 1920×1080。

## 反推链

1. 人眼看视频 → 画面在左上角
2. 打开 beat HTML 文件 → 单独看正常，但 `.scene` div 写了 `width:1280px;height:720px`
3. 为什么 LLM 写 1280×720？→ prompt 说了 1920×1080，但 LLM 偶尔自作主张
4. 为什么代码没拦住？→ `_single_llm_generate` 只在 `.scene` 不存在时注入新的，如果 LLM 已经写了 `.scene`（哪怕尺寸错），代码直接跳过
5. 为什么质量审查没发现？→ `motion_library.py` 的代码评分不检查宽高；LLM 审查采样只有 5 个，小概率抽中；quality_checker 只做 ffprobe

## 根因

**代码不校验 `.scene` div 的宽高**。LLM 偶尔写错尺寸，代码不纠正。

## 修复（2026-07-09）

在 `_single_llm_generate` 的包裹逻辑中，对已有的 `.scene` div 正则替换：
- `width:非1920` → `width:1920px`
- `height:非1080` → `height:1080px`

## 预防

- `scene_system.md` prompt 中加粗强调：`**scene div 的 width 必须是 1920px，height 必须是 1080px**`
- 代码层兜底：不管 LLM 写什么，最终强制修正
