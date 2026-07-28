"""
color_grader/impl.py — V1.0 电影级色彩分级
从4套赛博配色中选一，输出 color_grade.json
"""
import json, sys, os
from pathlib import Path

# ── 4套配色方案 ──
PALETTES = {
    "blade_runner": {
        "name": "Blade Runner 赛博雨夜",
        "background": "#0A0A2E",
        "surface": "#0D0221",
        "primary": "#00FFFF",
        "accent": "#FF00FF",
        "data": "#00CCFF",
        "text": "#E0E0FF",
        "text_secondary": "#8892B0",
        "glow": "rgba(0,255,255,0.3)",
        "grading": {
            "overlay": "linear-gradient(135deg, rgba(0,140,255,0.06), rgba(255,0,200,0.04))",
            "blend_mode": "overlay",
            "vignette": "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.65))",
            "chromatic_aberration": False,
        },
        "scanlines": False,
        "grain_intensity": 0.03,
    },
    "holographic": {
        "name": "Ghost in the Shell 全息界面",
        "background": "#020B1A",
        "surface": "#030F24",
        "primary": "#00FF41",
        "accent": "#FFB000",
        "data": "#00FF41",
        "text": "#CCFFCC",
        "text_secondary": "#5A8F5A",
        "glow": "rgba(0,255,65,0.35)",
        "grading": {
            "overlay": "linear-gradient(180deg, rgba(0,255,65,0.04), rgba(0,0,0,0))",
            "blend_mode": "screen",
            "vignette": "radial-gradient(ellipse at center, transparent 60%, rgba(2,11,26,0.8))",
            "chromatic_aberration": True,
        },
        "scanlines": True,
        "grain_intensity": 0.05,
    },
    "neon_noir": {
        "name": "Cyberpunk 2077 霓虹黑色",
        "background": "#0A0A0A",
        "surface": "#141414",
        "primary": "#FCEE09",
        "accent": "#FF007F",
        "data": "#00F0FF",
        "text": "#F0F0F0",
        "text_secondary": "#888888",
        "glow": "rgba(252,238,9,0.4)",
        "grading": {
            "overlay": "linear-gradient(135deg, rgba(252,238,9,0.04), rgba(255,0,127,0.03))",
            "blend_mode": "overlay",
            "vignette": "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.7))",
            "chromatic_aberration": False,
        },
        "scanlines": False,
        "grain_intensity": 0.04,
    },
    "apple_dark": {
        "name": "Apple Dark 克制高端",
        "background": "#000000",
        "surface": "#1C1C1E",
        "primary": "#0071E3",
        "accent": "#AF52DE",
        "data": "#64D2FF",
        "text": "#F5F5F7",
        "text_secondary": "#98989D",
        "glow": "rgba(0,113,227,0.25)",
        "grading": {
            "overlay": "linear-gradient(180deg, rgba(0,0,0,0.02), rgba(0,113,227,0.04))",
            "blend_mode": "overlay",
            "vignette": "radial-gradient(ellipse at center, transparent 65%, rgba(0,0,0,0.5))",
            "chromatic_aberration": False,
        },
        "scanlines": False,
        "grain_intensity": 0.02,
    },
    "apple_light": {
        "name": "Apple Light 干净明亮",
        "background": "#FAFAFA",
        "surface": "#FFFFFF",
        "primary": "#007AFF",
        "accent": "#5856D6",
        "data": "#007AFF",
        "text": "#1D1D1F",
        "text_secondary": "#86868B",
        "glow": "rgba(0,122,255,0.12)",
        "grading": {
            "overlay": "linear-gradient(180deg, rgba(0,122,255,0.02), rgba(88,86,214,0.02))",
            "blend_mode": "overlay",
            "vignette": "radial-gradient(ellipse at center, transparent 70%, rgba(0,0,0,0.03))",
            "chromatic_aberration": False,
        },
        "scanlines": False,
        "grain_intensity": 0.0,
    },
    "blue_purple": {
        "name": "Blue-Purple Tech 蓝紫渐层",
        "background": "#0A0A1A",
        "surface": "#0F0F2E",
        "primary": "#6C8CFF",
        "accent": "#A855F7",
        "data": "#6C8CFF",
        "text": "#E8ECFF",
        "text_secondary": "#8890B8",
        "glow": "rgba(108,140,255,0.25)",
        "grading": {
            "overlay": "linear-gradient(135deg, rgba(108,140,255,0.08), rgba(168,85,247,0.06))",
            "blend_mode": "overlay",
            "vignette": "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.55))",
            "chromatic_aberration": False,
        },
        "scanlines": False,
        "grain_intensity": 0.02,
    },
}

# 通用电影后期参数
FILM_POST = {
    "letterbox": True,          # 宽银幕上下黑边
    "letterbox_height": "5vh",  # 黑边高度（54px，对齐内容安全区）
    "grain_enabled": True,      # 胶片颗粒
    "grain_opacity": 0.04,      # 颗粒不透明度（会被方案覆盖）
    "vignette_enabled": True,   # 暗角
    "scanline_opacity": 0.03,   # 扫描线强度
}


def run(context: dict) -> dict:
    """选配色方案 → 生成 color_grade.json"""
    project_root = Path(context.get("project_root",
        Path(__file__).parent.parent.parent))
    output_dir = project_root / "output"
    
    # 读取 storyboard 的 mood
    sb_path = context.get("storyboard_path") or str(output_dir / "storyboard.json")
    with open(sb_path, encoding="utf-8") as f:
        sb = json.load(f)
    scenes = sb if isinstance(sb, list) else sb.get("scenes", [])
    
    # 提取 mood 关键词
    moods = []
    for s in scenes:
        m = s.get("mood", "")
        if m:
            moods.append(m.lower())
    mood_text = " | ".join(moods[:3])
    
    # ── 选配色 ──
    selection = _select_palette(mood_text)
    palette = PALETTES[selection]
    
    # ── 组装输出 ──
    grade = {
        "version": "v1.0",
        "selected": selection,
        "palette": {
            k: palette[k] for k in
            ["name", "background", "surface", "primary", "accent", "data", "text", "text_secondary", "glow"]
        },
        "grading": palette["grading"],
        "post": {
            **FILM_POST,
            "grain_opacity": palette["grain_intensity"],
            "scanlines": palette["scanlines"],
        },
        "_mood_input": mood_text,
    }
    
    # 保存
    out_path = output_dir / "color_grade.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(grade, f, ensure_ascii=False, indent=2)
    
    # 写回 context
    context["color_grade"] = grade
    context["color_grade_path"] = str(out_path)
    
    print(f"  [color-grader] 配色方案: {palette['name']} ({selection})")
    print(f"  [color-grader] 色调: bg={palette['background']} accent={palette['accent']}")
    return context


def _select_palette(mood_text: str) -> str:
    """根据 mood 关键词选择配色方案。默认苹果浅色。"""
    mood_lower = mood_text.lower()
    
    # 赛博/未来/科技/数字 → blade_runner（用户明确要暗黑赛博才触发）
    if any(w in mood_lower for w in ["赛博", "cyber", "futuristic"]):
        return "blade_runner"
    
    # 全息/hud/界面/冷酷 → holographic
    if any(w in mood_lower for w in ["全息", "hud", "holographic", "机械"]):
        return "holographic"
    
    # 霓虹/冲击/警示/黑暗 → neon_noir
    if any(w in mood_lower for w in ["霓虹", "neon", "暗黑", "dark"]):
        return "neon_noir"
    
    # 专业/克制/高端/简约/深沉 → apple_dark  
    if any(w in mood_lower for w in ["专业", "克制", "高端", "简约", "深沉", "professional", "minimal"]):
        return "apple_dark"
    
    # 默认：蓝紫渐层科技风
    return "blue_purple"
