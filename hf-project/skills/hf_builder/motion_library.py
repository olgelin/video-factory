"""
motion_library.py — V5.3 Motion Design 模板库
提供可复用的 GSAP 动画模板，按能量等级和视觉类型分类。

用法:
    from motion_library import get_motion_preset, generate_gsap_code
    preset = get_motion_preset("high_impact", "data_impact")
    gsap = generate_gsap_code(preset, element_ids)
"""

# ============================================================
# 能量等级 × 入场风格 矩阵
# ============================================================

MOTION_PRESETS = {
    # ── 高能量 ──
    "high_impact": {
        "energy": "high",
        "description": "冲击力入场 — 数字砸入 + 弹性回弹",
        "entry": {
            "title": {"from": "{y:80, opacity:0, duration:0.5, ease:'back.out(2.5)'}", "delay": 0},
            "number": {"from": "{scale:3, opacity:0, duration:0.6, ease:'back.out(1.7)'}", "delay": 0.15},
            "card": {"from": "{y:60, opacity:0, scale:0.9, duration:0.5, ease:'back.out(1.4)'}", "delay": 0.1, "stagger": 0.12},
            "badge": {"from": "{scale:0, opacity:0, duration:0.3, ease:'back.out(2)'}", "delay": 0.4, "stagger": 0.08},
            "subtitle": {"from": "{y:30, opacity:0, duration:0.4, ease:'power3.out'}", "delay": 0.5},
        },
        "breath": {"to": "{scale:1.03, duration:2, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": ".card"},
        "glow_pulse": {"to": "{textShadow:'0 0 50px rgba(255,215,0,0.9)', duration:1.5, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": "#main-number"},
        "best_for": ["data_impact", "dashboard", "compare", "ranking_board"],
    },

    "cinematic_reveal": {
        "energy": "high",
        "description": "电影感揭示 — 从暗到明 + 镜头推进",
        "entry": {
            "scene": {"from": "{opacity:0, scale:1.1, duration:1.0, ease:'power2.out'}", "delay": 0},
            "title": {"from": "{y:40, opacity:0, duration:0.7, ease:'power3.out'}", "delay": 0.3},
            "number": {"from": "{y:60, opacity:0, scale:1.5, duration:0.8, ease:'power4.out'}", "delay": 0.5},
            "card": {"from": "{y:50, opacity:0, duration:0.6, ease:'power2.out'}", "delay": 0.4, "stagger": 0.15},
            "badge": {"from": "{opacity:0, duration:0.5, ease:'power2.out'}", "delay": 0.7, "stagger": 0.1},
            "subtitle": {"from": "{y:20, opacity:0, duration:0.5, ease:'power2.out'}", "delay": 0.8},
        },
        "breath": {"to": "{scale:1.02, duration:3, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": ".scene"},
        "glow_pulse": {"to": "{textShadow:'0 0 40px rgba(0,212,255,0.7)', duration:2, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": "#main-number"},
        "best_for": ["quote_hero", "timeline_event", "product_showcase"],
    },

    "glitch_entry": {
        "energy": "high",
        "description": "故障风入场 — 抖动 + RGB 分离",
        "entry": {
            "title": {"from": "{x:-10, opacity:0, duration:0.3, ease:'steps(4)'}", "delay": 0},
            "number": {"from": "{scale:1.5, opacity:0, duration:0.4, ease:'back.out(2)'}", "delay": 0.1},
            "card": {"from": "{x:20, opacity:0, duration:0.3, ease:'power4.out'}", "delay": 0.15, "stagger": 0.08},
            "badge": {"from": "{scale:0, opacity:0, duration:0.2, ease:'back.out(3)'}", "delay": 0.3, "stagger": 0.05},
            "subtitle": {"from": "{x:-5, opacity:0, duration:0.3, ease:'steps(3)'}", "delay": 0.4},
        },
        "breath": {"to": "{x:'+=2', duration:0.1, repeat:3, yoyo:true, ease:'steps(1)'}", "target": ".card"},
        "glow_pulse": {"to": "{textShadow:'0 0 30px rgba(255,64,129,0.8)', duration:1, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": "#main-number"},
        "best_for": ["code_terminal", "hud", "market_ticker"],
    },

    # ── 中能量 ──
    "smooth_cascade": {
        "energy": "medium",
        "description": "流畅层叠 — 元素依次滑入",
        "entry": {
            "title": {"from": "{y:40, opacity:0, duration:0.6, ease:'power2.out'}", "delay": 0},
            "number": {"from": "{y:30, opacity:0, duration:0.5, ease:'power3.out'}", "delay": 0.2},
            "card": {"from": "{y:40, opacity:0, duration:0.5, ease:'power2.out'}", "delay": 0.3, "stagger": 0.15},
            "badge": {"from": "{y:20, opacity:0, duration:0.4, ease:'power2.out'}", "delay": 0.5, "stagger": 0.1},
            "subtitle": {"from": "{y:15, opacity:0, duration:0.4, ease:'power2.out'}", "delay": 0.6},
        },
        "breath": {"to": "{scale:1.02, duration:2.5, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": ".card"},
        "glow_pulse": {"to": "{textShadow:'0 0 30px rgba(0,212,255,0.5)', duration:2, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": "#main-number"},
        "best_for": ["dashboard", "flow", "list_alert", "data_impact"],
    },

    "fade_stagger": {
        "energy": "medium",
        "description": "渐入交错 — 优雅淡入 + 轻微位移",
        "entry": {
            "title": {"from": "{opacity:0, y:20, duration:0.7, ease:'power2.out'}", "delay": 0},
            "number": {"from": "{opacity:0, scale:0.95, duration:0.6, ease:'power2.out'}", "delay": 0.25},
            "card": {"from": "{opacity:0, y:25, duration:0.5, ease:'power2.out'}", "delay": 0.35, "stagger": 0.18},
            "badge": {"from": "{opacity:0, duration:0.4, ease:'power2.out'}", "delay": 0.6, "stagger": 0.12},
            "subtitle": {"from": "{opacity:0, y:10, duration:0.5, ease:'power2.out'}", "delay": 0.7},
        },
        "breath": {"to": "{opacity:0.9, duration:3, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": ".card"},
        "glow_pulse": {"to": "{textShadow:'0 0 25px rgba(168,85,247,0.5)', duration:2.5, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": "#main-number"},
        "best_for": ["flow", "timeline_event", "quote_hero"],
    },

    # ── 低能量/优雅 ──
    "elegant_float": {
        "energy": "low",
        "description": "优雅漂浮 — 缓慢浮现 + 呼吸",
        "entry": {
            "title": {"from": "{opacity:0, y:15, duration:1.0, ease:'sine.inOut'}", "delay": 0},
            "number": {"from": "{opacity:0, scale:0.98, duration:0.8, ease:'sine.inOut'}", "delay": 0.3},
            "card": {"from": "{opacity:0, y:20, duration:0.7, ease:'sine.inOut'}", "delay": 0.5, "stagger": 0.2},
            "badge": {"from": "{opacity:0, duration:0.6, ease:'sine.inOut'}", "delay": 0.8, "stagger": 0.15},
            "subtitle": {"from": "{opacity:0, y:10, duration:0.6, ease:'sine.inOut'}", "delay": 0.9},
        },
        "breath": {"to": "{scale:1.01, duration:4, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": ".scene"},
        "glow_pulse": {"to": "{textShadow:'0 0 20px rgba(201,169,110,0.4)', duration:3, repeat:-1, yoyo:true, ease:'sine.inOut'}", "target": "#main-number"},
        "best_for": ["quote_hero", "product_showcase"],
    },

    "typewriter_reveal": {
        "energy": "low",
        "description": "打字机揭示 — 逐字出现 + 光标闪烁",
        "entry": {
            "title": {"from": "{width:0, opacity:1, duration:1.5, ease:'steps(12)'}", "delay": 0},
            "number": {"from": "{opacity:0, duration:0.5, ease:'power2.out'}", "delay": 0.8},
            "card": {"from": "{opacity:0, y:15, duration:0.5, ease:'power2.out'}", "delay": 1.0, "stagger": 0.2},
            "badge": {"from": "{opacity:0, duration:0.4, ease:'power2.out'}", "delay": 1.3, "stagger": 0.15},
            "subtitle": {"from": "{opacity:0, duration:0.5, ease:'power2.out'}", "delay": 1.5},
        },
        "breath": None,
        "glow_pulse": None,
        "best_for": ["code_terminal", "quote_hero"],
    },
}

# ============================================================
# 视觉类型 → 推荐 motion preset
# ============================================================

VISUAL_TYPE_MOTION_MAP = {
    "data_impact": ["high_impact", "smooth_cascade"],
    "dashboard": ["smooth_cascade", "high_impact"],
    "compare": ["high_impact", "fade_stagger"],
    "flow": ["smooth_cascade", "fade_stagger"],
    "list_alert": ["smooth_cascade", "glitch_entry"],
    "hud": ["glitch_entry", "smooth_cascade"],
    "quote_hero": ["cinematic_reveal", "elegant_float"],
    "code_terminal": ["glitch_entry", "typewriter_reveal"],
    "ranking_board": ["high_impact", "smooth_cascade"],
    "product_showcase": ["cinematic_reveal", "elegant_float"],
    "timeline_event": ["cinematic_reveal", "fade_stagger"],
    "market_ticker": ["glitch_entry", "high_impact"],
}

# ============================================================
# 逐场景质量评分标准
# ============================================================

QUALITY_SCORING_RUBRIC = {
    "visual_density": {
        "weight": 20,
        "description": "视觉密度 — 可见元素数量",
        "scoring": {
            "10": "12+ 元素，含数据卡片+图表+装饰层",
            "8": "8-11 元素，含数据卡片+装饰层",
            "6": "5-7 元素，有基本数据展示",
            "4": "3-4 元素，信息稀疏",
            "2": "1-2 元素，大字报",
        },
    },
    "data_visualization": {
        "weight": 20,
        "description": "数据可视化 — 图表/进度条/趋势指标",
        "scoring": {
            "10": "含图表(chart_type)+进度条+趋势箭头+数字冲击",
            "8": "含进度条+趋势箭头+数字冲击",
            "6": "含数字+趋势箭头",
            "4": "只有数字，无可视化",
            "2": "无数据元素",
        },
    },
    "animation_quality": {
        "weight": 15,
        "description": "动画质量 — GSAP 入场数量+缓动多样性",
        "scoring": {
            "10": "8+ tl.from()，3+ 种缓动，含呼吸动画",
            "8": "6-7 tl.from()，2 种缓动",
            "6": "4-5 tl.from()，1 种缓动",
            "4": "2-3 tl.from()",
            "2": "0-1 tl.from()，静态",
        },
    },
    "color_harmony": {
        "weight": 15,
        "description": "色彩和谐 — 配色一致+饱和度+对比度",
        "scoring": {
            "10": "主色+强调色+数据色，饱和度≥60%，对比度≥21:1",
            "8": "2 种颜色，饱和度≥50%",
            "6": "1 种颜色，灰蒙蒙",
            "4": "颜色不协调",
            "2": "白色/浅色背景",
        },
    },
    "layout_structure": {
        "weight": 15,
        "description": "布局结构 — 三层视觉+安全区+分栏",
        "scoring": {
            "10": "背景层+内容层+装饰层，安全边距≥80px，分栏合理",
            "8": "两层结构，安全边距≥60px",
            "6": "一层结构，元素贴边",
            "4": "布局混乱",
            "2": "无布局",
        },
    },
    "typography": {
        "weight": 15,
        "description": "排版 — 字号层次+字体限制+发光",
        "scoring": {
            "10": "标题80-120px+数据100-140px+副标题36-48px，≤2种字体，有text-shadow",
            "8": "字号层次分明，有发光",
            "6": "字号层次一般",
            "4": "字号单一，无发光",
            "2": "字体过小/过大",
        },
    },
}


def get_motion_preset(energy: str = "medium", visual_type: str = "data_impact") -> dict:
    """根据能量等级和视觉类型获取推荐 motion preset"""
    # 先从 visual_type 推荐中选
    candidates = VISUAL_TYPE_MOTION_MAP.get(visual_type, ["smooth_cascade"])
    
    # 按能量匹配
    for name in candidates:
        preset = MOTION_PRESETS.get(name)
        if preset and preset["energy"] == energy:
            return preset
    
    # fallback: 返回第一个候选
    return MOTION_PRESETS.get(candidates[0], MOTION_PRESETS["smooth_cascade"])


def generate_gsap_code(preset: dict, element_ids: dict, composition_id: str) -> str:
    """从 motion preset 生成 GSAP 代码片段"""
    lines = [
        "var tl = gsap.timeline({paused:true});",
        f"var root = document.querySelector('[data-composition-id={composition_id}]') || document;",
    ]
    
    entry = preset.get("entry", {})
    for elem_type, config in entry.items():
        selector = element_ids.get(elem_type, f".{elem_type}")
        delay = config.get("delay", 0)
        stagger = config.get("stagger", 0)
        
        if stagger:
            lines.append(
                f"var {elem_type}s = root.querySelectorAll('{selector}');"
            )
            lines.append(
                f"{elem_type}s.forEach(function(el, i) {{"
            )
            lines.append(
                f"  tl.from(el, {config['from']}, {delay} + i * {stagger});"
            )
            lines.append("});")
        else:
            lines.append(
                f"tl.from(root.querySelector('{selector}'), {config['from']}, {delay});"
            )
    
    # 呼吸动画
    breath = preset.get("breath")
    if breath:
        lines.append(
            f"tl.to(root.querySelector('{breath['target']}'), {breath['to']}, 0.8);"
        )
    
    # 发光脉动
    glow = preset.get("glow_pulse")
    if glow:
        lines.append(
            f"tl.to(root.querySelector('{glow['target']}'), {glow['to']}, 0.5);"
        )
    
    lines.append(f"window.__timelines = window.__timelines || {{}};")
    lines.append(f'window.__timelines["{composition_id}"] = tl;')
    
    return "\n".join(lines)


def score_scene_quality(html: str, scene: dict) -> dict:
    """V5.3: 逐场景质量评分（0-100）"""
    import re
    
    scores = {}
    details = {}
    
    # 1. 视觉密度
    element_count = len(re.findall(r'<(div|span|h[1-6]|p|svg)', html))
    if element_count >= 12:
        scores["visual_density"] = 10
    elif element_count >= 8:
        scores["visual_density"] = 8
    elif element_count >= 5:
        scores["visual_density"] = 6
    elif element_count >= 3:
        scores["visual_density"] = 4
    else:
        scores["visual_density"] = 2
    details["element_count"] = element_count
    
    # 2. 数据可视化
    has_chart = bool(re.search(r'(bar|chart|pie|kpi|progress|trend)', html, re.I))
    has_progress = 'progress' in html.lower() or 'width:0' in html
    has_trend = bool(re.search(r'[↑↓↗↘]', html))
    has_number_impact = 'scale:2' in html or 'scale:3' in html or 'scale: 2' in html
    
    if has_chart and has_progress and has_trend and has_number_impact:
        scores["data_visualization"] = 10
    elif has_progress and has_trend and has_number_impact:
        scores["data_visualization"] = 8
    elif has_number_impact or has_trend:
        scores["data_visualization"] = 6
    elif 'font-size:1' in html or 'font-size: 1' in html:
        scores["data_visualization"] = 4
    else:
        scores["data_visualization"] = 2
    details["has_chart"] = has_chart
    details["has_progress"] = has_progress
    
    # 3. 动画质量
    gsap_from_count = len(re.findall(r'\.from\(', html))
    eases = set(re.findall(r"ease:'([^']+)'", html))
    has_breath = 'repeat:-1' in html and 'yoyo:true' in html
    
    if gsap_from_count >= 8 and len(eases) >= 3 and has_breath:
        scores["animation_quality"] = 10
    elif gsap_from_count >= 6 and len(eases) >= 2:
        scores["animation_quality"] = 8
    elif gsap_from_count >= 4:
        scores["animation_quality"] = 6
    elif gsap_from_count >= 2:
        scores["animation_quality"] = 4
    else:
        scores["animation_quality"] = 2
    details["gsap_from_count"] = gsap_from_count
    details["ease_types"] = list(eases)
    
    # 4. 色彩和谐
    hex_colors = set(re.findall(r'#[0-9a-fA-F]{6}', html))
    has_deep_bg = '#1a1a2e' in html or '#0a0a0a' in html
    has_glow = 'text-shadow' in html
    has_accent = len([c for c in hex_colors if c not in ('#1a1a2e', '#0a0a0a', '#ffffff', '#FFFFFF')]) >= 2
    
    if has_deep_bg and has_accent and has_glow and len(hex_colors) >= 4:
        scores["color_harmony"] = 10
    elif has_deep_bg and has_accent and len(hex_colors) >= 3:
        scores["color_harmony"] = 8
    elif has_deep_bg and len(hex_colors) >= 2:
        scores["color_harmony"] = 6
    elif has_deep_bg:
        scores["color_harmony"] = 4
    else:
        scores["color_harmony"] = 2
    details["color_count"] = len(hex_colors)
    
    # 5. 布局结构
    has_scene_div = 'class="scene"' in html or "class='scene'" in html
    has_overflow = 'overflow:hidden' in html
    has_z_index = bool(re.search(r'z-index:\s*[0-9]', html))
    has_padding = bool(re.search(r'padding:\s*[6-9][0-9]|padding:\s*1[0-9]{2}', html))
    
    if has_scene_div and has_overflow and has_z_index and has_padding:
        scores["layout_structure"] = 10
    elif has_scene_div and has_overflow and has_z_index:
        scores["layout_structure"] = 8
    elif has_scene_div and has_overflow:
        scores["layout_structure"] = 6
    elif has_scene_div:
        scores["layout_structure"] = 4
    else:
        scores["layout_structure"] = 2
    
    # 6. 排版
    has_large_title = bool(re.search(r'font-size:\s*(8[0-9]|9[0-9]|1[0-4][0-9])px', html))
    has_large_data = bool(re.search(r'font-size:\s*(1[0-4][0-9])px', html))
    has_text_shadow = 'text-shadow' in html
    font_families = set(re.findall(r"font-family:'([^']+)'", html))
    
    if has_large_title and has_large_data and has_text_shadow and len(font_families) <= 2:
        scores["typography"] = 10
    elif has_large_title and has_text_shadow and len(font_families) <= 2:
        scores["typography"] = 8
    elif has_large_title:
        scores["typography"] = 6
    elif has_text_shadow:
        scores["typography"] = 4
    else:
        scores["typography"] = 2
    
    # 加权总分
    total = 0
    for key, rubric in QUALITY_SCORING_RUBRIC.items():
        total += scores.get(key, 0) * rubric["weight"] / 100
    
    return {
        "total_score": round(total * 10, 1),
        "dimensions": scores,
        "details": details,
        "grade": _grade(total * 10),
    }


def _grade(score: float) -> str:
    if score >= 85:
        return "A — 优秀"
    elif score >= 70:
        return "B — 良好"
    elif score >= 55:
        return "C — 合格"
    elif score >= 40:
        return "D — 需改进"
    else:
        return "F — 不合格"
