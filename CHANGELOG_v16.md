# V35 — 输出双版本(1080p+4K) + 字幕字号回退

## 变更日期
2026-08-23

## 问题背景
1. 用户要像 video-clip-pro 一样输出两个版本：1080p + 4K。
2. V34 的字幕字号自适应（4K FontSize×2=40）导致字幕超级大（占画面 21.9%），用户反馈"字幕变得超级大"。

## 变更内容
- `audio_mixer/impl.py`：
  - 回退字幕字号自适应，保持 FontSize=20（ffmpeg 自动缩放，4K 下约 8-10%，不再超级大）
  - 新增双版本输出：4K 成品额外缩一个 1080p 版本 → step11_final.mp4(1080p) + step11_final_2x.mp4(4K)

## 验证
- 端到端：4K 输入跑 audio_mixer，输出 step11_final.mp4(1920×1080) + step11_final_2x.mp4(3840×2160)，都有声音+字幕
- 字幕字号：FontSize=20 回退后字幕约 8-10%（对比 FontSize=40 的 21.9% 超级大）

---

# V34 — 修复 video2x 4K 成品被误丢弃 + 字幕字号自适应

## 变更日期
2026-08-23

## 问题背景
video2x 完成 2x 超分后、进程退出时崩溃（exit 3221225477，ncnn-vulkan 访问冲突），但 4K 文件已完整产出（step10_upscaled.mp4，3840×2160，106.6s）。旧判定 `returncode==0 才算成功` 误判失败，管线退回 1080p，4K 成品被白白丢弃。

## 变更内容
- `video_upscaler/impl.py`：成功判定从 `returncode==0` 改为"输出文件有效性"——新增 `_check_upscale_valid()`，检查时长完整(≥95%)+分辨率达到 scale 倍。video2x 完成超分后退出才崩，文件完整即采用 4K；真中途崩（文件不完整）仍 fallback 1080p。
- `audio_mixer/impl.py burn_subtitles`：字幕字号自适应（4K 宽 3840 → FontSize=40，1080p 保持 20），timeout 180s→600s（4K 烧字幕重编码更慢）。

## 验证
- 单测 `_check_upscale_valid`：4K 文件 valid=True(3840x2160)，不存在文件 valid=False
- 4K + 音轨合成：3840×2160 + aac，链路通
- 4K 烧字幕：路径转义后 FontSize 20/40 均成功，保留 4K
- 端到端：手动用 4K 输入跑 audio_mixer，成品 step11_final.mp4 = 3840×2160 + 声音 + 字幕，全部通过

---

# V21 — 修复跨 script timeline 作用域断裂（偶发空白帧根因）

## 变更日期
2026-08-23

## 问题背景
用户反馈 short_video 完整管道偶发"空白帧"（某场景画面无内容）。深挖定位真正根因：LLM 偶发把 GSAP timeline 定义(var tl)和 __timelines 注册拆到不同 <script> 块，导致注册处 tl 跨 script 作用域断裂（undefined），HyperFrames 等 45s 认为 timeline 未注册 → 渲染出静态空白帧（sub_timeline_readiness_timeout 警告）。

排查排除的误判：密度爆表（坏场景密度正常仍空白）、tl.play 重复（带不带 tl.play 都空白）、JS 语法错误（node --check 通过）。

## 变更内容
- `hf_builder/impl.py _single_llm_generate`：新增跨 script timeline 作用域修复——timeline 定义后暴露到全局 `window.__tl`，`__timelines` 注册处统一用 `window.__tl` 引用。无论 LLM 拆几个 script，注册都能拿到真正的 timeline 对象（正常场景同样适用，window.__tl === tl 无害）。

## 验证
- 活坏场景 beat-2 手动修复：动画 1.31%→3.29%、亮彩 0.60%→3.22%，渲染 99.6s→33.6s，无 readiness 警告。
- test_scenes.py（AI 话题 2 场景）：均触发修复，动画 12.12%/10.16%、亮彩 6.09%/4.19%，正常。
- 多话题交叉验证（科普 + 消费 2 场景）：动画 8.02%/10.49%、亮彩 3.47%/3.56%，正常。

---

# V20 — 竖屏 prompt 布局（news_vertical 隔离目录）

## 变更日期
2026-08-22

## 问题背景
渲染层已参数化（V18），但 prompt 层 few-shot / 安全区 / Three.js setSize 仍是横屏 1920×1080，竖屏下 LLM 布局偏横屏。

## 变更内容
- 新增 `prompts/news_vertical/` 目录（从 news 复制活跃文件，横屏 `news/` 一字不动，物理隔离）
- `news_vertical/scene_system.md`：few-shot div 1080×1920、安全区左右 54px / 上下 96px
- `news_vertical/scene_threejs.md`：5 处 `setSize(1080,1920)` + `PerspectiveCamera` aspect `1080/1920`
- `impl.py _load_scene_prompts()`：竖屏（`_VIDEO_H > _VIDEO_W`）优先加载 `{style}_vertical` 目录，不存在则 fallback 原目录（不报错）

## 验证
- 单元测试 3 项：竖屏正确加载 news_vertical（无横屏残留）、横屏回归正常（未被污染）、edu 无竖屏目录安全 fallback

---

# V19 — hold≥1s 呼吸（关键信息落定后静止）

## 变更日期
2026-08-22

## 问题背景
卡片场景"一直在动"：关键信息（主标题/大数字）入场后立刻进入 repeat 呼吸抖动，观众看不清内容，显得廉价。借鉴 video-shotcraft 的"关键信息落定后 hold≥1s 呼吸"规则（见 70-经验/2026-08-21-视频开源项目借鉴审计）。

## 变更内容
- `prompts/news/scene_animation.md`「基础动效规范」新增一条铁律：关键信息（主标题/大数字/核心内容）入场落定后先静止 ≥1s（不呼吸、不抖动、不缩放），呼吸动画起始时间 = 入场结束 + 1s；氛围元素（粒子雨/扫光/光晕）不受此限，可从入场后持续动。

## 验证
- test_scenes.py 测 2 场景（compare + data_impact），hold 约束方向正确：
  - compare：主标题落定后静止，呼吸给仪表指针（3.8s）和粒子雨（0.3s）
  - data_impact：大数字落定后仅静态发光，呼吸给 gauge（2.5s）和光晕（0.5s）
- 关键信息先静止、氛围元素持续动，呼吸起始时间明显推迟。

---

# V18 — 竖屏渲染修复（--vertical 失效）

## 变更日期
2026-08-20

## 问题背景
`--vertical` 竖屏模式失效：配置正确传入了 video_width=1080/video_height=1920，但渲染层仍输出 1920×1080 横屏。

根因：`hf_builder/impl.py` 生成 HTML 的多处硬编码了 `1920×1080`（SCENE_PROMPT 硬性规则、_single_llm_generate 的 W/H 与 _fix_scene_wh、fallback 模板、intro/outro 模板、index.html），未参数化，把竖屏配置覆盖回横屏。

## 变更内容
- `SCENE_PROMPT` 硬性规则 `data-width="1920" data-height="1080"` → `data-width="{W}" data-height="{H}"`（format 已传 W/H）
- `_single_llm_generate`：`W, H = 1920, 1080` → `W, H = _VIDEO_W, _VIDEO_H`；`_fix_scene_wh` 与注入 .scene 用 W/H 变量
- `fallback_scene_html`、`_auto_fix`、`build_intro_html`、`build_outro_html`、`build_index_html` 的硬编码 1920/1080 → `{_VIDEO_W}`/`{_VIDEO_H}` 或 replace 替换
- 横屏模式（默认）零影响：W/H=1920/1080 时行为与之前完全一致

## 已知遗留（后续完善）
- `prompts/news/scene_system.md` 等 few-shot 示例 + Three.js setSize 仍按横屏设计，竖屏下 LLM 布局可能仍偏横屏，需单独重新设计竖屏 few-shot

---

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
