"""
motion_director/impl.py — V1.0 镜头运动 + 文字动画时间线
"""
import json, random
from pathlib import Path

# 镜头运动库
CAMERA_MOVES = {
    "dolly_in":    {"gsap": "translateZ", "from": -200, "to": 0,   "perspective": 1200, "ease": "power3.inOut"},
    "dolly_out":   {"gsap": "translateZ", "from": 0,   "to": -200, "perspective": 1200, "ease": "power3.inOut"},
    "crane_down":  {"gsap": "y",          "from": -40,  "to": 0,   "perspective": 1000, "ease": "power2.out"},
    "push_right":  {"gsap": "x",          "from": -60,  "to": 0,   "perspective": 1000, "ease": "power3.out"},
    "dutch_tilt":  {"gsap": "rotateZ",    "from": 3,    "to": 0,   "perspective": 1000, "ease": "power2.inOut"},
    "static":      None,
}

# 文字动画库
TEXT_ANIMS = {
    "stagger_blur": {
        "target": "chars",
        "gsap": {
            "opacity": 0, "filter": "blur(10px)", "y": 50,
            "stagger": {"each": 0.03, "from": "center"},
            "duration": 0.6, "ease": "power3.out",
        },
    },
    "fade_up": {
        "target": "element",
        "gsap": {"opacity": 0, "y": 30, "duration": 0.7, "ease": "power3.out"},
    },
    "scale_bounce": {
        "target": "element",
        "gsap": {"scale": 0, "duration": 0.6, "ease": "back.out(1.7)"},
    },
    "glitch_in": {
        "target": "element",
        "gsap": {"x": "random(-5,5)", "opacity": 0, "duration": 0.15, "repeat": 2, "yoyo": True, "ease": "steps(3)"},
    },
    "typewriter": {
        "target": "chars",
        "gsap": {"opacity": 0, "stagger": 0.05, "duration": 0.3, "ease": "steps(1)"},
    },
}

# visual_type → 推荐镜头运动
TYPE_CAMERA = {
    "data_impact":    "dolly_in",
    "compare":        "push_right",
    "flow":           "crane_down",
    "quote_hero":     "dolly_in",
    "list_alert":     "dutch_tilt",
    "timeline_event": "push_right",
}

# visual_type → 主文字动画
TYPE_TITLE_ANIM = {
    "data_impact":    "stagger_blur",
    "compare":        "fade_up",
    "flow":           "stagger_blur",
    "quote_hero":     "stagger_blur",
    "list_alert":     "glitch_in",
    "timeline_event": "fade_up",
}

# visual_type → 数据/数字动画
TYPE_DATA_ANIM = {
    "data_impact":    "scale_bounce",
    "compare":        "scale_bounce",
    "flow":           "fade_up",
    "quote_hero":     None,
    "list_alert":     "scale_bounce",
    "timeline_event": "fade_up",
}

# 呼吸动画（可选，用于卡片）
BREATH_ANIM = {
    "enabled": True,
    "target": ".card, .hud-card, .node, .rank-item",
    "gsap": {"scale": 1.02, "duration": 3, "repeat": -1, "yoyo": True, "ease": "sine.inOut"},
}


def run(context: dict) -> dict:
    project_root = Path(context.get("project_root",
        Path(__file__).parent.parent.parent))
    output_dir = project_root / "output"

    # 读 storyboard
    with open(context.get("storyboard_path") or str(output_dir / "storyboard.json"), encoding="utf-8") as f:
        sb = json.load(f)
    scenes = sb if isinstance(sb, list) else sb.get("scenes", [])

    # 读 layout_plan
    lp_path = context.get("layout_plan_path") or str(output_dir / "layout_plan.json")
    with open(lp_path, encoding="utf-8") as f:
        lp = json.load(f)

    plan = {"version": "v1.0", "scenes": [], "global": {"breath": BREATH_ANIM}}

    for s in scenes:
        sid = s.get("scene_id", 0)
        vt = s.get("visual_type", "data_impact")
        duration = s.get("duration", 10.0)

        cam_key = TYPE_CAMERA.get(vt, "static")
        cam = CAMERA_MOVES.get(cam_key)

        title_anim = TYPE_TITLE_ANIM.get(vt, "stagger_blur")
        data_anim = TYPE_DATA_ANIM.get(vt)

        plan["scenes"].append({
            "scene_id": sid,
            "visual_type": vt,
            "duration": duration,
            "camera": {
                "move": cam_key,
                "params": cam,
                "start_at": 0.1 * duration,
                "end_at": 0.9 * duration,
            } if cam else {"move": "static"},
            "animations": {
                "title": {"type": title_anim, "params": TEXT_ANIMS[title_anim]},
                "data":  {"type": data_anim, "params": TEXT_ANIMS[data_anim]} if data_anim else None,
                "cards": {"stagger": 0.15, "y_offset": 30, "ease": "back.out(1.4)"},
                "decor": {"stagger": 0.08, "opacity_from": 0, "duration": 0.5},
            },
        })

    out_path = output_dir / "motion_plan.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    context["motion_plan"] = plan
    context["motion_plan_path"] = str(out_path)
    print(f"  [motion-director] {len(plan['scenes'])} 场景, 镜头+文字动画已分配")
    return context
