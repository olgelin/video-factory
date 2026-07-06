#!/usr/bin/env python3
"""
visual_director/impl.py — V6.0 电影级视觉导演（合并 color_grader + layout_composer + motion_director + depth_composer）

单一 skill，产出 visual_plan.json（包含 color / layout / motion / depth 全部维度）。

输入: storyboard.json
输出: output/visual_plan.json
"""
import json
import os
import sys
from pathlib import Path

# ══════════════════════════════════════════════════════════
# 1. Color — 4套电影配色
# ══════════════════════════════════════════════════════════
PALETTES = {
    "blade_runner": {
        "name": "Blade Runner 赛博雨夜",
        "background": "#0A0A2E", "surface": "#0D0221",
        "primary": "#00FFFF", "accent": "#FF00FF", "data": "#00CCFF",
        "text": "#E0E0FF", "text_secondary": "#8892B0",
        "glow": "rgba(0,255,255,0.3)",
        "grading": {
            "overlay": "linear-gradient(135deg, rgba(0,140,255,0.06), rgba(255,0,200,0.04))",
            "blend_mode": "overlay",
            "vignette": "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.65))",
        },
        "scanlines": False, "grain_intensity": 0.03,
    },
    "holographic": {
        "name": "Ghost in the Shell 全息界面",
        "background": "#020B1A", "surface": "#030F24",
        "primary": "#00FF41", "accent": "#FFB000", "data": "#00FF41",
        "text": "#CCFFCC", "text_secondary": "#5A8F5A",
        "glow": "rgba(0,255,65,0.35)",
        "grading": {
            "overlay": "linear-gradient(180deg, rgba(0,255,65,0.04), rgba(0,0,0,0))",
            "blend_mode": "screen",
            "vignette": "radial-gradient(ellipse at center, transparent 60%, rgba(2,11,26,0.8))",
        },
        "scanlines": True, "grain_intensity": 0.05,
    },
    "neon_noir": {
        "name": "Cyberpunk 2077 霓虹黑色",
        "background": "#0A0A0A", "surface": "#141414",
        "primary": "#FCEE09", "accent": "#FF007F", "data": "#00F0FF",
        "text": "#F0F0F0", "text_secondary": "#888888",
        "glow": "rgba(252,238,9,0.4)",
        "grading": {
            "overlay": "linear-gradient(135deg, rgba(252,238,9,0.04), rgba(255,0,127,0.03))",
            "blend_mode": "overlay",
            "vignette": "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.7))",
        },
        "scanlines": False, "grain_intensity": 0.04,
    },
    "apple_dark": {
        "name": "Apple Dark 克制高端",
        "background": "#000000", "surface": "#1C1C1E",
        "primary": "#0071E3", "accent": "#AF52DE", "data": "#64D2FF",
        "text": "#F5F5F7", "text_secondary": "#98989D",
        "glow": "rgba(0,113,227,0.25)",
        "grading": {
            "overlay": "linear-gradient(180deg, rgba(0,0,0,0.02), rgba(0,113,227,0.04))",
            "blend_mode": "overlay",
            "vignette": "radial-gradient(ellipse at center, transparent 65%, rgba(0,0,0,0.5))",
        },
        "scanlines": False, "grain_intensity": 0.02,
    },
    "apple_light": {
        "name": "Apple Light 干净明亮",
        "background": "#FAFAFA", "surface": "#FFFFFF",
        "primary": "#007AFF", "accent": "#5856D6", "data": "#007AFF",
        "text": "#1D1D1F", "text_secondary": "#86868B",
        "glow": "rgba(0,122,255,0.12)",
        "grading": {
            "overlay": "linear-gradient(180deg, rgba(0,122,255,0.02), rgba(88,86,214,0.02))",
            "blend_mode": "overlay",
            "vignette": "radial-gradient(ellipse at center, transparent 70%, rgba(0,0,0,0.03))",
        },
        "scanlines": False, "grain_intensity": 0.0,
    },
}

# ══════════════════════════════════════════════════════════
# 2. Layout — 构图规则
# ══════════════════════════════════════════════════════════
COMPOSITION_RULES = {
    "blade_runner":  {"negative_space": 0.35, "density_bias": 0.0},
    "holographic":   {"negative_space": 0.25, "density_bias": 0.5},
    "neon_noir":     {"negative_space": 0.40, "density_bias": -0.5},
    "apple_dark":    {"negative_space": 0.45, "density_bias": 0.0},
    "apple_light":   {"negative_space": 0.45, "density_bias": -0.3},
}

DEPTH_PRESETS = {
    "background": {"scale": 0.88, "blur_px": 8,  "z": -200, "parallax": 0.2},
    "midground":  {"scale": 1.0,  "blur_px": 0,  "z": 0,    "parallax": 0.5},
    "foreground": {"scale": 1.15, "blur_px": 4,  "z": 100,  "parallax": 0.8},
    "hero":       {"scale": 1.0,  "blur_px": 0,  "z": 50,   "parallax": 1.0},
}

# ══════════════════════════════════════════════════════════
# 3. Motion — 镜头 + 动画
# ══════════════════════════════════════════════════════════
CAMERA_MOVES = {
    "dolly_in":    {"gsap": "translateZ", "from": -200, "to": 0,   "perspective": 1200, "ease": "power3.inOut"},
    "dolly_out":   {"gsap": "translateZ", "from": 0,   "to": -200, "perspective": 1200, "ease": "power3.inOut"},
    "crane_down":  {"gsap": "y",          "from": -40,  "to": 0,   "perspective": 1000, "ease": "power2.out"},
    "push_right":  {"gsap": "x",          "from": -60,  "to": 0,   "perspective": 1000, "ease": "power3.out"},
    "dutch_tilt":  {"gsap": "rotateZ",    "from": 3,    "to": 0,   "perspective": 1000, "ease": "power2.inOut"},
    "static":      None,
}

TYPE_CAMERA = {
    "data_impact": "dolly_in", "compare": "push_right", "flow": "crane_down",
    "quote_hero": "dolly_in", "list_alert": "dutch_tilt", "timeline_event": "push_right",
}

# ══════════════════════════════════════════════════════════
# 4. Depth — z-index 体系
# ══════════════════════════════════════════════════════════
Z_INDEX_SYSTEM = {
    "ui_overlay": 1000, "vignette": 900, "light_leaks": 800,
    "grain": 700, "letterbox": 600, "foreground": 100,
    "hero_content": 50, "midground": 10, "background_decor": 5, "background": 1,
}

DECOR_ELEMENTS = {
    "particle_field": {
        "enabled": True, "z": 5, "parallax": 0.3,
        "css": "position:absolute;inset:0;opacity:0.15;pointer-events:none",
    },
    "grid_overlay": {
        "enabled": True, "z": 3, "parallax": 0.2,
        "css": "position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,0.02) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.02) 1px,transparent 1px);background-size:80px 80px;pointer-events:none",
    },
    "radial_glow": {
        "enabled": True, "z": 2, "parallax": 0.25,
        "css": "position:absolute;top:50%;left:50%;width:900px;height:900px;transform:translate(-50%,-50%);background:radial-gradient(circle,{ACCENT_GLOW},transparent 70%);border-radius:50%;pointer-events:none",
    },
}

def _select_palette(mood_text: str) -> str:
    """根据 mood 选择配色方案。默认苹果浅色。"""
    mood_lower = mood_text.lower()
    if any(w in mood_lower for w in ["赛博", "未来", "沉浸", "cyber", "futuristic"]):
        return "blade_runner"
    if any(w in mood_lower for w in ["全息", "hud", "界面", "holographic"]):
        return "holographic"
    if any(w in mood_lower for w in ["霓虹", "暗黑", "neon", "dark"]):
        return "neon_noir"
    if any(w in mood_lower for w in ["专业", "克制", "高端", "简约", "冷静", "professional", "minimal", "深沉", "低调"]):
        return "apple_dark"
    # 默认：苹果浅色 —— 数据、清晰、深度、思考、对比、警示、紧张 等全都用浅色
    return "apple_light"


def run(context: dict) -> dict:
    """主入口：产出统一的 visual_plan.json。"""
    project_root = Path(context.get("project_root",
        Path(__file__).parent.parent.parent))
    output_dir = project_root / "output"

    # 读 storyboard
    sb_path = context.get("storyboard_path") or str(output_dir / "storyboard.json")
    with open(sb_path, encoding="utf-8") as f:
        sb = json.load(f)
    scenes = sb if isinstance(sb, list) else sb.get("scenes", [])

    # ── 1. 选配色 ──
    moods = [s.get("mood", "") for s in scenes[:3] if s.get("mood")]
    mood_text = " | ".join(moods)
    palette_key = _select_palette(mood_text)
    palette = PALETTES[palette_key]
    print(f"  [visual-director] 配色: {palette['name']} ({palette_key})")

    # ── 2. 构图 ──
    comp_rule = COMPOSITION_RULES.get(palette_key, COMPOSITION_RULES["blade_runner"])

    # ── 构建每场景计划 ──
    plan_scenes = []
    for s in scenes:
        sid = s.get("scene_id", 0)
        vt = s.get("visual_type", "data_impact")
        duration = s.get("duration", 10.0)

        cam_key = TYPE_CAMERA.get(vt, "static")
        cam = CAMERA_MOVES.get(cam_key)

        plan_scenes.append({
            "scene_id": sid,
            "visual_type": vt,
            "duration": duration,
            "color": {
                k: palette[k] for k in
                ["name", "background", "surface", "primary", "accent", "data", "text", "text_secondary", "glow"]
            },
            "grading": palette["grading"],
            "layout": {
                "rule_of_thirds": True,
                "golden_ratio_focus": True,
                "negative_space_ratio": comp_rule["negative_space"],
                "depth": DEPTH_PRESETS,
                "density_adjust": comp_rule["density_bias"],
            },
            "motion": {
                "camera_move": cam_key,
                "camera_params": cam,
            },
            "depth": {
                "layers": Z_INDEX_SYSTEM,
                "decor": DECOR_ELEMENTS,
            },
        })

    visual_plan = {
        "version": "v6.0",
        "palette": palette_key,
        "palette_name": palette["name"],
        "post": {
            "letterbox": True, "letterbox_height": "10vh",
            "grain_enabled": True, "grain_opacity": palette["grain_intensity"],
            "vignette_enabled": True, "scanlines": palette["scanlines"],
        },
        "scenes": plan_scenes,
    }

    out_path = output_dir / "visual_plan.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(visual_plan, f, ensure_ascii=False, indent=2)

    context["visual_plan"] = visual_plan
    context["visual_plan_path"] = str(out_path)
    context["_color_grade"] = visual_plan  # 兼容旧 hf_builder

    print(f"  [visual-director] ✅ {len(plan_scenes)} 场景, 配色={palette_key}")
    return context


if __name__ == "__main__":
    ctx = {"project_root": str(Path(__file__).parent.parent.parent)}
    run(ctx)
    print("✅ visual_director 测试完成")
