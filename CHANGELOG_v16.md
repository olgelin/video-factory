# V16 — 系统性质量修复

## 变更日期
2026-07-31

## 问题背景
p13 管道审计发现 2 个 LLM 导致的问题：
1. beat-8 / outro 使用独立 `gsap.to()` 而非 `tl.to()`，HyperFrames seek 不同步
2. beat-8 光标缺 `left` 定位

根因：`scene_system.md` prompt 中的示例代码使用了 `gsap.to()` 和 `repeat:-1`，LLM 忠实照搬。

## 变更内容

### 1. prompt 修复 (`scene_system.md`)
- 所有 `gsap.to()` / `gsap.from()` 示例 → `tl.to()` / `tl.from()`
- 所有 `repeat:-1` 示例 → `repeat:3`
- 禁止项新增两条：
  - 🔴 所有动画必须用 `tl.to()`/`tl.from()`/`tl.fromTo()` — 禁止独立 `gsap.to()`/`gsap.from()` 在 tl 时间线外
  - 🔴 禁止 `repeat:-1`（无限循环）— 所有 repeat 必须是正整数 ≤5

### 2. prompt 拆分（328行 → 4文件）
- `scene_system.md` — 核心规则 + 布局 + 禁止项 (140行)
- `scene_animation.md` — 高级技法 + 动效规范 + 加分细节 (60行)
- `scene_threejs.md` — Three.js 3D 技法模板 (150行)
- `_load_scene_prompts()` 自动拼接子文件

### 3. 生成后自动校验 (`impl.py` → `_validate_post_gen`)
- 独立 `gsap.to()`/`gsap.from()` → 自动替换为 `tl.to()`/`tl.from()`
- `repeat:-1` 残留 → 自动替换为 `repeat:3`
- 绝对定位缺 `left` 的元素 → 自动注入 `left:50%;transform:translateX(-50%)`
- 在 `_single_llm_generate()` 中，`_fix_repeat_infinite` 之后调用

### 4. 原有函数修复
- `_fix_repeat_infinite`: 修复了 `repeat:(\\d+)` 被 patch 工具双重转义的 bug

## 测试
- `_validate_post_gen` 单元测试 4/4 通过
- prompt 拼装验证 6/6 通过
- 管道回归测试（steps 1-10）

## 回滚
- 恢复 `scene_system.md.bak_v16_pre_split`
- 恢复 `impl.py` 到 git HEAD 或 `scene_system.md.bak3` 版本
