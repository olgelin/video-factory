# Storyboard Skill 修复计划

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 修改storyboard skill，输出hf-builder需要的完整字段格式

**问题：** storyboard输出字段名与hf-builder期望的不匹配
- voiceover_text → narration
- timestamp → duration
- choreography → animations
- transition_in/transition_out → transition

**Tech Stack:** Python, JSON

---

### Task 1: 检查当前storyboard输出格式

**Objective:** 确认当前storyboard.json的实际字段

**Files:**
- Read: `E:\Hermes-Agent\workspace\xiaoshan\video-factory\hf-project\output\storyboard.json`

**Step 1: 读取当前storyboard**

```python
import json
with open('output/storyboard.json', 'r', encoding='utf-8') as f:
    sb = json.load(f)
print(f'Scene 1 keys: {list(sb[0].keys())}')
```

**Expected Output:**
```
Scene 1 keys: ['scene_id', 'visual_type', 'concept', 'mood', 'choreography', 'transition_in', 'transition_out', 'depth_layers', 'density_target', 'key_elements', 'voiceover_text', 'timestamp']
```

---

### Task 2: 检查hf-builder期望的格式

**Objective:** 确认hf-builder需要的字段名

**Files:**
- Read: `E:\Hermes-Agent\workspace\xiaoshan\video-factory\hf-project\skills\step09b_hf_render\impl.py`

**Step 1: 搜索narration和duration**

```bash
grep -n "narration\|duration" skills/step09b_hf_render/impl.py | head -20
```

**Expected Output:**
```
256:            "narration": s.get("narration", ""),
384:            "duration": s.get("duration", 4.0),
```

---

### Task 3: 修改storyboard skill输出格式

**Objective:** 修改storyboard skill，输出hf-builder需要的字段

**Files:**
- Modify: `E:\Hermes-Agent\workspace\xiaoshan\video-factory\hf-project\skills\storyboard\impl.py`

**Step 1: 在generate_storyboard函数中添加字段转换**

在`generate_storyboard`函数末尾，保存storyboard之前，添加字段转换逻辑：

```python
# 转换字段名，匹配hf-builder期望的格式
for scene in storyboard:
    # voiceover_text → narration
    if "voiceover_text" in scene and "narration" not in scene:
        scene["narration"] = scene.pop("voiceover_text")
    
    # timestamp → duration
    if "timestamp" in scene and "duration" not in scene:
        ts = scene.pop("timestamp")
        if isinstance(ts, dict) and "start" in ts and "end" in ts:
            scene["duration"] = ts["end"] - ts["start"]
    
    # choreography → animations
    if "choreography" in scene and "animations" not in scene:
        scene["animations"] = scene.pop("choreography")
    
    # transition_in/transition_out → transition
    if "transition_in" in scene or "transition_out" in scene:
        scene["transition"] = {
            "in": scene.pop("transition_in", ""),
            "out": scene.pop("transition_out", "")
        }
```

**Step 2: 测试修改后的storyboard**

```bash
cd E:\Hermes-Agent\workspace\xiaoshan\video-factory\hf-project
python -c "
import sys; sys.path.insert(0, 'skills')
from storyboard import impl
result = impl.run({})
print('Scene 1 keys:', list(result.get('storyboard', [{}])[0].keys()))
"
```

**Expected Output:**
```
Scene 1 keys: ['scene_id', 'visual_type', 'concept', 'mood', 'animations', 'transition', 'depth_layers', 'density_target', 'key_elements', 'narration', 'duration']
```

---

### Task 4: 重新生成storyboard

**Objective:** 用修改后的skill重新生成storyboard.json

**Files:**
- Regenerate: `E:\Hermes-Agent\workspace\xiaoshan\video-factory\hf-project\output\storyboard.json`

**Step 1: 运行storyboard skill**

```bash
cd E:\Hermes-Agent\workspace\xiaoshan\video-factory\hf-project
python -c "
import sys; sys.path.insert(0, 'skills')
from storyboard import impl
result = impl.run({})
print(f'Storyboard: {len(result.get(\"storyboard\", []))} scenes')
"
```

**Step 2: 验证输出格式**

```bash
python -c "
import json
with open('output/storyboard.json', 'r', encoding='utf-8') as f:
    sb = json.load(f)
scene = sb[0]
print(f'narration: {\"narration\" in scene}')
print(f'duration: {\"duration\" in scene}')
print(f'animations: {\"animations\" in scene}')
print(f'transition: {\"transition\" in scene}')
"
```

**Expected Output:**
```
narration: True
duration: True
animations: True
transition: True
```

---

### Task 5: 测试hf-builder

**Objective:** 用新的storyboard测试hf-builder

**Files:**
- Test: `E:\Hermes-Agent\workspace\xiaoshan\video-factory\hf-project\skills\step09b_hf_render\impl.py`

**Step 1: 运行hf-builder**

```bash
cd E:\Hermes-Agent\workspace\xiaoshan\video-factory\hf-project
python -c "
import sys; sys.path.insert(0, 'skills')
from step09b_hf_render import impl
result = impl.run({})
print(f'HTML: {result.get(\"index_html_path\", \"N/A\")}')
print(f'Video: {result.get(\"video_path\", \"N/A\")}')
"
```

**Expected Output:**
```
HTML: E:\Hermes-Agent\workspace\xiaoshan\video-factory\hf-project\hf_render_project\index.html
Video: E:\Hermes-Agent\workspace\xiaoshan\video-factory\hf-project\hf_render_project\rendered.mp4
```

---

## 验证步骤

1. **storyboard.json格式正确** - 包含narration、duration、animations、transition字段
2. **hf-builder能正确读取** - 不再报错或使用默认值
3. **渲染视频成功** - 生成完整的视频文件
