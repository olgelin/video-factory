"""快速测试 2-3 场景的 HTML 质量，不跑完整管道"""
import sys, json, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'hf-project', 'skills', 'hf_builder'))
from impl import _load_scene_prompts, _single_llm_generate

# 从最近的 storyboard 取前 3 个场景
storyboard_path = os.path.join(os.path.dirname(__file__), 'hf-project', 'output', 'storyboard.json')
if not os.path.exists(storyboard_path):
    print("❌ 没找到 storyboard.json，先跑一次 --steps 1-9 生成分镜")
    sys.exit(1)

with open(storyboard_path, 'r', encoding='utf-8') as f:
    sb = json.load(f)

scenes = sb.get('scenes', sb) if isinstance(sb, dict) else sb
if isinstance(scenes, dict):
    scenes = list(scenes.values())
scenes = scenes[:2]  # 只测前 2 个

print(f"测试 {len(scenes)} 个场景...")
sys_prompt, user_tmpl = _load_scene_prompts()
print(f"system prompt: {len(sys_prompt)}c\n")

for i, scene in enumerate(scenes):
    sid = i + 1
    scene['duration'] = scene.get('duration', 10.0)
    print(f"--- Scene {sid} ---")
    html = _single_llm_generate(scene, sid, model="deepseek-v4-pro")
    if html:
        out = f"hf-project/hf_render_project/compositions/beat-{sid}.html"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  ✅ {len(html)}c → {out}")
    else:
        print(f"  ❌ 生成失败")
