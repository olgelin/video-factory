"""
depth_composer/impl.py — V1.0 z-index层级 + 视差倍率 + 装饰元素
"""
import json
from pathlib import Path

# 统一 z-index 体系
Z_INDEX_SYSTEM = {
    "ui_overlay":   1000,
    "vignette":     900,
    "light_leaks":  800,
    "grain":        700,
    "letterbox":    600,
    "foreground":   100,
    "hero_content": 50,
    "midground":    10,
    "background_decor": 5,
    "background":   1,
}

# 通用装饰元素配置
DECOR_ELEMENTS = {
    "particle_field": {
        "enabled": True,
        "z": 5,
        "parallax": 0.3,
        "css": "position:absolute;inset:0;opacity:0.15;pointer-events:none",
    },
    "grid_overlay": {
        "enabled": True,
        "z": 3,
        "parallax": 0.2,
        "css": "position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,0.02) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.02) 1px,transparent 1px);background-size:80px 80px;pointer-events:none",
    },
    "radial_glow": {
        "enabled": True,
        "z": 2,
        "parallax": 0.25,
        "css": "position:absolute;top:50%;left:50%;width:900px;height:900px;transform:translate(-50%,-50%);background:radial-gradient(circle,{ACCENT_GLOW},transparent 70%);border-radius:50%;pointer-events:none",
    },
    "light_traces": {
        "enabled": False,
        "z": 6,
        "parallax": 0.5,
        "css": "position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none",
    },
}

# 场景元素 → z-index 映射
ELEMENT_Z_MAP = {
    "title":       "hero_content",
    "headline":    "hero_content",
    "main_number": "hero_content",
    "quote":       "hero_content",
    "data_cards":  "midground",
    "cards":       "midground",
    "items":       "midground",
    "tags":        "midground",
    "subtitle":    "midground",
    "decor_lines": "background_decor",
    "bg_glow":     "background",
    "grid":        "background_decor",
    "particles":   "background_decor",
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
    palette = cg.get("palette", {})
    glow = palette.get("glow", "rgba(0,255,255,0.3)")

    plan = {
        "version": "v1.0",
        "z_index_system": Z_INDEX_SYSTEM,
        "decor": DECOR_ELEMENTS,
        "element_map": ELEMENT_Z_MAP,
        "scenes": [],
    }

    for s in scenes:
        sid = s.get("scene_id", 0)
        layers = s.get("depth_layers", {})

        # 从 storyboard 的 depth_layers 提取图层名
        scene_z = {}
        if isinstance(layers, dict):
            for layer_name, desc in layers.items():
                # 中文图层名 → 标准化
                norm = layer_name.strip()
                if any(w in norm for w in ["背景", "background", "bg"]):
                    scene_z[norm] = Z_INDEX_SYSTEM["background"]
                elif any(w in norm for w in ["前景", "foreground", "fg"]):
                    scene_z[norm] = Z_INDEX_SYSTEM["foreground"]
                elif any(w in norm for w in ["内容", "核心", "中景", "content", "mid"]):
                    scene_z[norm] = Z_INDEX_SYSTEM["hero_content"]
                else:
                    scene_z[norm] = Z_INDEX_SYSTEM["midground"]

        plan["scenes"].append({
            "scene_id": sid,
            "layers": scene_z,
        })

    out_path = output_dir / "depth_plan.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    context["depth_plan"] = plan
    context["depth_plan_path"] = str(out_path)
    print(f"  [depth-composer] {len(plan['scenes'])} 场景, z-index体系已分配")
    return context
