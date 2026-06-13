# hf_builder Skill 升级计划

> **For Hermes:** 按任务顺序执行，每个任务完成后验证。

**Goal:** 让 hf_builder 稳定产出高质量场景 HTML — 并行生成、prompt 强化、重试校验。

**Architecture:** ThreadPoolExecutor 并行调 LLM → 校验 HTML 质量 → 不合格重试 → 渲染

**Tech Stack:** Python ThreadPoolExecutor, DeepSeek/MIMO API, HyperFrames CLI

---

### Task 1: 并行 LLM 调用

**Objective:** 用 ThreadPoolExecutor 同时生成多个场景的 HTML，提升效率。

**File:** `skills/hf_builder/impl.py`

**改动：** 在 `run()` 函数中，把 `for i, scene in enumerate(scenes)` 循环改成并行：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def generate_and_build(scene, sid, total):
    result = generate_scene_content(scene, sid, total)
    html = build_scene_html(sid, scene, total, result)
    return sid, html

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(generate_and_build, s, i+1, total): i+1 for i, s in enumerate(scenes)}
    for future in as_completed(futures):
        sid, html = future.result()
        with open(compositions_dir / f"beat-{sid}.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  [{sid}/{total}] {len(html)} chars")
```

**注意：** max_workers=3（DeepSeek 有并发限制，不要超过 3）

---

### Task 2: Prompt 强化 — 按 visual_type 强制组件

**Objective:** 根据 visual_type 强制要求 LLM 生成特定组件，解决"dashboard 没有进度条"问题。

**File:** `skills/hf_builder/impl.py` — `SYSTEM_PROMPT` 和 `generate_scene_content()`

**在 SYSTEM_PROMPT 末尾添加：**

```
## 按视觉类型的强制组件要求

dashboard（仪表盘）：必须包含至少2个 .card + 至少1个 .progress-bar + .main-num
compare（对比）：必须包含 .vs-left 和 .vs-right 两个面板
data_impact（数据冲击）：必须包含 .main-num（大数字发光）+ 至少2个 .card
quote_hero（金句）：必须包含 .title（大字）+ .subtitle + 至少1个 .card 或 .badge
flow（流程）：必须包含至少3个 .panel 或 .card 表示流程步骤
hud（HUD）：必须包含 .stat 或 .metric 数据指标
list_alert（列表）：必须包含至少3个 .card 或 .item

如果生成的 HTML 不满足以上要求，会被判定为不合格并重新生成。
```

**在 prompt 中也添加：**

```
## 必须满足的组件（visual_type: {visual_type}）
{component_requirements}
```

其中 `component_requirements` 根据 visual_type 动态生成。

---

### Task 3: 亮度约束

**Objective:** 解决"场景太暗看不见"问题。

**File:** `skills/hf_builder/impl.py` — `SYSTEM_PROMPT`

**在 prompt 中添加：**

```
## 亮度约束（强制）
- 主标题：color 必须是 #ffffff 或 #06b6d4，opacity 必须 1.0
- 副标题：color rgba(255,255,255,0.7) 以上
- 数据卡片背景：rgba(255,255,255,0.08) 以上（不能太透明）
- 数据文字：必须有 text-shadow 或 color 为亮色（#06b6d4/#ffffff）
- 禁止所有文字 opacity < 0.5
```

---

### Task 4: HTML 质量校验 + 重试

**Objective:** 生成后检查 HTML 质量，不合格自动重试（最多3次）。

**File:** `skills/hf_builder/impl.py`

**新增函数：**

```python
def validate_html(html: str, visual_type: str) -> tuple[bool, str]:
    """校验 HTML 质量，返回 (通过, 原因)"""
    import re
    
    # 1. 检查 class 名数量（至少3个不同的动画 class）
    ANIM_CLASSES = {'title', 'subtitle', 'main-num', 'card', 'data-card',
                    'tag', 'badge', 'progress-bar', 'stat', 'metric',
                    'panel', 'vs-left', 'vs-right', 'heading', 'bar'}
    found = set()
    for m in re.finditer(r'class="([^"]+)"', html):
        for c in m.group(1).split():
            if c in ANIM_CLASSES:
                found.add(c)
    if len(found) < 2:
        return False, f"只有{len(found)}个动画class，需要至少2个"
    
    # 2. 检查中文文字（至少5个中文字符）
    chinese = re.findall(r'[\u4e00-\u9fff]+', html)
    total_chars = sum(len(c) for c in chinese)
    if total_chars < 5:
        return False, f"只有{total_chars}个中文字符，内容不足"
    
    # 3. 按 visual_type 检查必须的组件
    requirements = {
        'dashboard': ['card', 'progress-bar'],
        'compare': ['vs-left', 'vs-right'],
        'data_impact': ['main-num', 'card'],
        'quote_hero': ['title'],
        'flow': ['panel', 'card'],
        'hud': ['stat', 'metric'],
    }
    required = requirements.get(visual_type, [])
    missing = [r for r in required if r not in found]
    if missing:
        return False, f"缺少必须组件: {missing}"
    
    return True, "OK"
```

**在 generate_scene_content 中加重试：**

```python
def generate_scene_content_with_retry(scene, scene_id, total, max_retries=3):
    visual_type = scene.get("visual_type", "hero")
    for attempt in range(max_retries):
        result = generate_scene_content(scene, scene_id, total)
        html = result.get("html", "")
        ok, reason = validate_html(html, visual_type)
        if ok:
            return result
        print(f"  ⚠️ 尝试{attempt+1}/{max_retries}不合格: {reason}，重试...")
    print(f"  ❌ {max_retries}次尝试均不合格，使用最后一次")
    return result
```

---

### Task 5: 更新 run() 函数集成所有改进

**Objective:** 把 Task 1-4 的改动整合到 run() 函数中。

**File:** `skills/hf_builder/impl.py` — `run()` 函数

---

### Task 6: 测试验证

**Objective:** 跑完整流程，验证并行+重试+校验都正常工作。

**Command:**
```bash
cd E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project
python skills/hf_builder/impl.py
```

**验证：**
1. 日志显示并行生成（多个场景同时开始）
2. 不合格场景有重试日志
3. 最终视频所有场景都有内容（无白屏）
4. 用 vision_analyze 检查之前有问题的场景（2和4）是否改善
