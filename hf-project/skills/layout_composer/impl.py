"""
layout_composer/impl.py — V1.0 布局骨架选择 + 构图规则 + 景深分层
"""
import json
from pathlib import Path

# 模板→visual_type 映射
TEMPLATE_MAP = {
    "data_impact":    "data_impact",
    "compare":        "compare",
    "flow":           "flow",
    "quote_hero":     "quote_hero",
    "list_alert":     "list_alert",
    "timeline_event": "timeline_event",
    "hud":            "hud",
    "ranking_board":  "ranking_board",
    "opening":        "opening",
}

# 构图规则 — 不同配色对应不同负空间比例
COMPOSITION_RULES = {
    "blade_runner":  {"negative_space": 0.35, "density_bias": 0.0},
    "holographic":   {"negative_space": 0.25, "density_bias": +0.5},
    "neon_noir":     {"negative_space": 0.40, "density_bias": -0.5},
    "apple_dark":    {"negative_space": 0.45, "density_bias": 0.0},
}

# 景深预设
DEPTH_PRESETS = {
    "background": {"scale": 0.88, "blur_px": 8,  "z": -200, "parallax": 0.2},
    "midground":  {"scale": 1.0,  "blur_px": 0,  "z": 0,    "parallax": 0.5},
    "foreground": {"scale": 1.15, "blur_px": 4,  "z": 100,  "parallax": 0.8},
    "hero":       {"scale": 1.0,  "blur_px": 0,  "z": 50,   "parallax": 1.0},
}


def run(context: dict) -> dict:
    project_root = Path(context.get("project_root",
        Path(__file__).parent.parent.parent))
    output_dir = project_root / "output"

    # 读 storyboard
    with open(context.get("storyboard_path") or str(output_dir / "storyboard.json"), encoding="utf-8") as f:
        sb = json.load(f)
    scenes = sb if isinstance(sb, list) else sb.get("scenes", [])

    # 读 color_grade
    cg_path = context.get("color_grade_path") or str(output_dir / "color_grade.json")
    with open(cg_path, encoding="utf-8") as f:
        cg = json.load(f)
    palette_key = cg.get("selected", "blade_runner")
    comp_rule = COMPOSITION_RULES.get(palette_key, COMPOSITION_RULES["blade_runner"])

    plan = {"version": "v1.0", "scenes": []}

    for s in scenes:
        sid = s.get("scene_id", 0)
        vt = s.get("visual_type", "data_impact")
        template = TEMPLATE_MAP.get(vt, "data_impact")

        plan["scenes"].append({
            "scene_id": sid,
            "visual_type": vt,
            "template": template,
            "composition": {
                "rule_of_thirds": True,
                "golden_ratio_focus": True,
                "negative_space_ratio": comp_rule["negative_space"],
            },
            "depth": DEPTH_PRESETS,
            "density_adjust": comp_rule["density_bias"],
        })

    out_path = output_dir / "layout_plan.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    context["layout_plan"] = plan
    context["layout_plan_path"] = str(out_path)
    print(f"  [layout-composer] {len(plan['scenes'])} 场景, 配色={palette_key}")
    return context
