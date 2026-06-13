"""
scene_templates.py — 赛博科技风模板系统 v3
读取 design.md + design_specs.json 驱动，不硬编码。

设计DNA（from design.md + HF best practices）:
- 背景：#1a1a2e 深蓝 + 网格 + ghost text + 光晕
- 主色：#00D4FF 电光蓝（来自 design.md）
- 辅色：#FF6B6B 珊瑚红
- 数据色：#4ECDC4
- 标题：160-180px（来自 design_specs）
- 字体：JetBrains Mono 用于数据
- 动画：GSAP 驱动（SLAMS/CASCADES/COUNTS UP 等）
"""

import re

# ============================================================
# 设计系统颜色 — 默认值，可被 design.md 覆盖
# ============================================================
_default_colors = {
    "primary": "#00D4FF",
    "secondary": "#FF6B6B",
    "data": "#4ECDC4",
    "accent": "#FF6B6B",
    "bg": "#1a1a2e",
    "text": "#FFFFFF",
    "text_secondary": "#A0A0B0",
}

def set_design_colors(design: dict):
    global _default_colors
    if design and "colors" in design:
        _default_colors.update(design["colors"])

def _c(key: str) -> str:
    return _default_colors.get(key, "#00D4FF")

def _hex_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 6:
        return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"
    return "0,212,255"

def _glow(hex_color: str, alpha: float = 0.5) -> str:
    return f"rgba({_hex_rgb(hex_color)},{alpha})"

# 场景间颜色轮换
def _accent(scene_id: int) -> dict:
    p, s, d = _c("primary"), _c("secondary"), _c("data")
    sets = [
        {"p": p, "s": s},
        {"p": s, "s": p},
        {"p": d, "s": p},
        {"p": p, "s": d},
        {"p": s, "s": d},
    ]
    return sets[(scene_id - 1) % len(sets)]


# ============================================================
# GSAP 动画映射（来自 design_specs 的 animation verbs）
# ============================================================

_ANIM_VERBS = {
    "SLAMS": {"from": "{y:60, opacity:0, duration:0.5, ease:'back.out(2)'}", "stagger": 0},
    "CRASHES": {"from": "{scale:1.5, opacity:0, duration:0.4, ease:'power4.out'}", "stagger": 0},
    "PUNCHES": {"from": "{scale:0, opacity:0, duration:0.3, ease:'back.out(3)'}", "stagger": 0},
    "CASCADES": {"from": "{y:-40, opacity:0, duration:0.6, ease:'power2.out'}", "stagger": 0.1},
    "DROPS": {"from": "{y:-80, opacity:0, duration:0.5, ease:'bounce.out'}", "stagger": 0.08},
    "SLIDES": {"from": "{x:-60, opacity:0, duration:0.5, ease:'power3.out'}", "stagger": 0.1},
    "FLOATS": {"from": "{y:30, opacity:0, duration:0.8, ease:'sine.out'}", "stagger": 0.15},
    "MORPHS": {"from": "{scale:0.8, opacity:0, borderRadius:'50%', duration:0.6, ease:'power2.out'}", "stagger": 0.1},
    "COUNTS UP": {"from": "{textContent:0, duration:1, ease:'power1.out', snap:{textContent:1}}", "stagger": 0},
    "GLOWS": {"from": "{opacity:0, textShadow:'0 0 0px transparent', duration:0.8, ease:'power2.out'}", "stagger": 0.1},
    "BREATHES": {"from": "{scale:0.95, opacity:0, duration:1, ease:'sine.inOut'}", "stagger": 0.2},
    "PULSES": {"from": "{scale:0.9, opacity:0, duration:0.6, ease:'sine.inOut'}", "stagger": 0.1},
}

def generate_gsap(animations: dict, composition_id: str, duration: float = 8.0) -> str:
    """根据 animation 动词生成 GSAP 入场动画代码"""
    if not animations:
        animations = {"标题": "SLAMS", "副标题": "CASCADES", "数据": "FLOATS", "装饰": "PULSES"}

    anims = []
    selector_map = {
        "标题": "h1, h2",
        "副标题": "p.subtitle, .subtitle",
        "数据": ".stat, .card, .metric, .item",
        "装饰": ".badge, .tag, .deco",
    }

    for role, verb in animations.items():
        sel = selector_map.get(role, "h1")
        anim_cfg = _ANIM_VERBS.get(verb, _ANIM_VERBS["FLOATS"])
        delay = 0 if role == "标题" else 0.2 if role == "副标题" else 0.3
        anims.append(
            f'tl.from("[data-composition-id={composition_id}] {sel}", {anim_cfg["from"]}, {delay});'
        )

    return "\n      ".join(anims)


# ============================================================
# 转场效果映射（来自 design_specs 的 transition）
# ============================================================

def generate_transition_css(transition: dict) -> str:
    """根据 transition 类型生成 CSS 转场效果"""
    if not transition:
        return ""
    trans_in = transition.get("in", "")
    # 转场通过 GSAP 实现，这里只返回 CSS 准备
    return ""


# ============================================================
# 基础组件
# ============================================================

def _stat_card(num: str, label: str, bar_pct: int = 70, accent: str = None, title_size: int = 52) -> str:
    if accent is None: accent = _c("primary")
    return f'''<div style="flex:1;background:{accent}08;backdrop-filter:blur(10px);
      border:1px solid {accent}25;border-radius:16px;padding:24px;
      box-shadow:0 0 20px {accent}10;">
      <div class="stat" style="font-size:{title_size}px;font-weight:900;color:{accent};
        text-shadow:0 0 30px {_glow(accent)},0 0 60px {_glow(accent, 0.3)};
        font-family:'JetBrains Mono',monospace;line-height:1;">{num}</div>
      <div style="font-size:16px;color:{_c('text_secondary')};margin-top:8px;letter-spacing:1px;">{label}</div>
      <div style="width:100%;height:4px;background:rgba(255,255,255,0.06);border-radius:2px;margin-top:12px;">
        <div style="width:{bar_pct}%;height:100%;background:linear-gradient(90deg,{accent},{_c('data')});
          border-radius:2px;box-shadow:0 0 8px {_glow(accent, 0.4)};"></div>
      </div>
    </div>'''

def _badge(text: str, accent: str = None) -> str:
    if accent is None: accent = _c("primary")
    return f'''<span class="badge" style="display:inline-block;background:{accent}15;color:{accent};
      padding:6px 16px;border-radius:20px;font-size:14px;font-weight:600;
      border:1px solid {accent}30;letter-spacing:1px;">{text}</span>'''

def _divider(accent: str = None) -> str:
    if accent is None: accent = _c("primary")
    return f'<div style="width:100%;height:1px;background:linear-gradient(90deg,transparent,{accent}40,transparent);margin:8px 0;"></div>'

def _ghost_text(text: str, accent: str = None) -> str:
    """Ghost text — 大字低透明度装饰"""
    if accent is None: accent = _c("primary")
    return f'''<div style="position:absolute;top:15%;right:5%;font-size:140px;font-weight:900;
      color:{accent}06;letter-spacing:10px;pointer-events:none;z-index:1;
      font-family:'Inter',sans-serif;">{text}</div>'''

def _grid_overlay(accent: str = None) -> str:
    if accent is None: accent = _c("primary")
    return f'''<div style="position:absolute;top:0;left:0;width:100%;height:100%;
      background-image:
        linear-gradient({accent}06 1px, transparent 1px),
        linear-gradient(90deg, {accent}06 1px, transparent 1px);
      background-size:80px 80px;pointer-events:none;z-index:1;"></div>'''

def _scanlines() -> str:
    return '''<div style="position:absolute;top:0;left:0;width:100%;height:100%;
      background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.03) 2px,rgba(0,0,0,0.03) 4px);
      pointer-events:none;z-index:10;"></div>'''

def _corner_brackets(accent: str = None) -> str:
    if accent is None: accent = _c("primary")
    return f'''<div style="position:absolute;top:30px;left:30px;width:20px;height:20px;border-right:2px solid {accent}30;border-bottom:2px solid {accent}30;"></div>
    <div style="position:absolute;top:30px;right:30px;width:20px;height:20px;border-left:2px solid {accent}30;border-bottom:2px solid {accent}30;"></div>
    <div style="position:absolute;bottom:30px;left:30px;width:20px;height:20px;border-right:2px solid {accent}30;border-top:2px solid {accent}30;"></div>
    <div style="position:absolute;bottom:30px;right:30px;width:20px;height:20px;border-left:2px solid {accent}30;border-top:2px solid {accent}30;"></div>'''


# ============================================================
# 7种场景模板 — 接受 design_specs 参数
# ============================================================

def template_data_impact(title: str, subtitle: str, stats: list, tags: list = None,
                         scene_id: int = 1, title_size: int = 96, **kw) -> str:
    a = _accent(scene_id)
    p, s = a["p"], a["s"]

    cards = ""
    for i, st in enumerate(stats[:4]):
        bar = st.get("bar_pct", 60 + i * 10)
        cards += _stat_card(st["num"], st.get("label", ""), bar, p if i % 2 == 0 else s, title_size=48)

    badges = ""
    if tags:
        items = "".join(_badge(t, p if i % 2 == 0 else s) for i, t in enumerate(tags[:5]))
        badges = f'<div class="deco" style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;">{items}</div>'

    return f'''<div class="scene-content" style="display:flex;flex-direction:column;width:100%;height:100%;
      padding:80px 100px;box-sizing:border-box;gap:28px;justify-content:center;
      font-family:'Inter','Noto Sans SC',sans-serif;">
      {_grid_overlay(p)}
      {_scanlines()}
      {_ghost_text("DATA", p)}
      {_corner_brackets(p)}
      <div style="text-align:center;position:relative;z-index:2;">
        <h1 style="font-size:{title_size}px;font-weight:900;color:{_c('text')};
          text-shadow:0 0 30px {_glow(p)},0 0 60px {_glow(p, 0.3)};
          line-height:1.1;margin:0;">{title}</h1>
      </div>
      <div style="display:flex;gap:16px;position:relative;z-index:2;">{cards}</div>
      <p class="subtitle" style="font-size:22px;color:{_c('text_secondary')};text-align:center;
        line-height:1.6;max-width:1000px;margin:0 auto;position:relative;z-index:2;">{subtitle}</p>
      {badges}
    </div>'''


def template_dashboard(title: str, subtitle: str, metrics: list, tags: list = None,
                       scene_id: int = 1, title_size: int = 96, **kw) -> str:
    a = _accent(scene_id)
    p, s = a["p"], a["s"]

    top_cards = ""
    for i, m in enumerate(metrics[:3]):
        bar = m.get("bar_pct", 70 + i * 8)
        top_cards += _stat_card(m["num"], m.get("label", ""), bar, p if i != 1 else s, title_size=44)

    return f'''<div class="scene-content" style="display:flex;flex-direction:column;width:100%;height:100%;
      padding:60px 80px;box-sizing:border-box;gap:20px;font-family:'Inter','Noto Sans SC',sans-serif;">
      {_grid_overlay(p)}
      {_scanlines()}
      {_ghost_text("METRICS", p)}
      <div style="text-align:center;position:relative;z-index:2;">
        <h2 style="font-size:{title_size}px;font-weight:900;color:{_c('text')};
          text-shadow:0 0 20px {_glow(p)};margin:0;">{title}</h2>
        <p class="subtitle" style="font-size:18px;color:{_c('text_secondary')};margin:8px 0 0 0;">{subtitle}</p>
        {_divider(p)}
      </div>
      <div style="display:flex;gap:16px;flex:1;position:relative;z-index:2;">{top_cards}</div>
    </div>'''


def template_compare(title: str, left_items: list, right_items: list,
                     left_heading: str = "A", right_heading: str = "B",
                     scene_id: int = 1, title_size: int = 96, **kw) -> str:
    a = _accent(scene_id)
    lc, rc = a["p"], a["s"]

    def _side(items: list, heading: str, color: str) -> str:
        rows = ""
        for i, item in enumerate(items[:4]):
            rows += f'''<div style="display:flex;align-items:center;gap:12px;padding:14px 18px;
              background:{color}08;border:1px solid {color}15;border-radius:10px;">
              <div style="width:36px;height:36px;border-radius:8px;background:{color}20;
                display:flex;align-items:center;justify-content:center;
                font-size:18px;font-weight:800;color:{color};">{i+1}</div>
              <div style="font-size:22px;color:{_c('text')};font-weight:600;">{item}</div>
            </div>'''
        return f'''<div style="flex:1;display:flex;flex-direction:column;gap:12px;">
          <div style="text-align:center;padding:20px;background:{color}10;
            border:1px solid {color}25;border-radius:12px;">
            <div style="font-size:32px;font-weight:900;color:{color};
              text-shadow:0 0 20px {_glow(color, 0.6)};">{heading}</div>
          </div>
          {rows}
        </div>'''

    return f'''<div class="scene-content" style="display:flex;flex-direction:column;width:100%;height:100%;
      padding:60px 80px;box-sizing:border-box;gap:24px;justify-content:center;
      font-family:'Inter','Noto Sans SC',sans-serif;">
      {_grid_overlay(lc)}
      {_ghost_text("VS", lc)}
      <h1 style="font-size:{title_size}px;font-weight:900;color:{_c('text')};text-align:center;
        text-shadow:0 0 20px {_glow(lc)};margin:0;position:relative;z-index:2;">{title}</h1>
      <div style="display:flex;gap:24px;flex:1;align-items:stretch;position:relative;z-index:2;">
        {_side(left_items, left_heading, lc)}
        <div style="display:flex;align-items:center;justify-content:center;padding:0 8px;">
          <div style="font-size:64px;font-weight:900;color:{_c('text')};
            text-shadow:0 0 30px {_glow(lc)},0 0 60px {_glow(rc)};">VS</div>
        </div>
        {_side(right_items, right_heading, rc)}
      </div>
    </div>'''


def template_quote_hero(quote: str, subtitle: str, accent_label: str = "",
                       tags: list = None, scene_id: int = 1, title_size: int = 96, **kw) -> str:
    a = _accent(scene_id)
    p, s = a["p"], a["s"]

    accent_html = ""
    if accent_label:
        accent_html = f'''<div style="display:flex;align-items:center;gap:12px;justify-content:center;">
          <div style="width:60px;height:2px;background:linear-gradient(90deg,transparent,{p});"></div>
          <span class="deco" style="font-size:14px;color:{p};letter-spacing:3px;font-weight:600;">{accent_label}</span>
          <div style="width:60px;height:2px;background:linear-gradient(90deg,{p},transparent);"></div>
        </div>'''

    badges = ""
    if tags:
        items = "".join(_badge(t, p if i % 2 == 0 else s) for i, t in enumerate(tags[:4]))
        badges = f'<div class="deco" style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;">{items}</div>'

    return f'''<div class="scene-content" style="display:flex;flex-direction:column;width:100%;height:100%;
      padding:100px 140px;box-sizing:border-box;gap:24px;justify-content:center;align-items:center;
      font-family:'Inter','Noto Sans SC',sans-serif;">
      {_grid_overlay(p)}
      {_ghost_text("QUOTE", s)}
      {_corner_brackets(p)}
      <div style="position:relative;z-index:2;display:flex;flex-direction:column;align-items:center;gap:20px;">
        {accent_html}
        <h1 style="font-size:{title_size}px;font-weight:900;color:{_c('text')};text-align:center;
          text-shadow:0 0 30px {_glow(p)},0 0 60px {_glow(p, 0.3)};
          line-height:1.2;max-width:1100px;margin:0;">{quote}</h1>
        <p class="subtitle" style="font-size:22px;color:{_c('text_secondary')};text-align:center;
          line-height:1.6;max-width:800px;margin:0;">{subtitle}</p>
        {badges}
      </div>
    </div>'''


def template_hud(title: str, stats: list, center_label: str = "",
                 scene_id: int = 1, title_size: int = 96, **kw) -> str:
    a = _accent(scene_id)
    p, s = a["p"], a["s"]

    positions = [
        "top:80px;left:80px;", "top:80px;right:80px;",
        "bottom:120px;left:80px;", "bottom:120px;right:80px;"
    ]
    corner_html = ""
    for i, st in enumerate(stats[:4]):
        pos = positions[i] if i < len(positions) else positions[0]
        color = p if i % 2 == 0 else s
        corner_html += f'''<div style="position:absolute;{pos}text-align:center;
          background:{color}08;border:1px solid {color}20;border-radius:12px;
          padding:16px 24px;backdrop-filter:blur(8px);">
          <div class="stat" style="font-size:44px;font-weight:900;color:{color};
            text-shadow:0 0 20px {_glow(color, 0.6)};font-family:'JetBrains Mono',monospace;">{st["num"]}</div>
          <div style="font-size:14px;color:{_c('text_secondary')};margin-top:4px;letter-spacing:1px;">{st.get("label","")}</div>
        </div>'''

    center = ""
    if center_label:
        center = f'''<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;">
          <div style="font-size:{title_size}px;font-weight:900;color:{_c('text')};
            text-shadow:0 0 40px {_glow(p)},0 0 80px {_glow(p, 0.3)};">{center_label}</div>
        </div>'''

    return f'''<div class="scene-content" style="position:relative;width:100%;height:100%;
      font-family:'Inter','Noto Sans SC',sans-serif;">
      {_grid_overlay(p)}
      {_scanlines()}
      {_ghost_text("MONITOR", p)}
      <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
        width:280px;height:280px;border:1px solid {p}15;border-radius:50%;
        box-shadow:0 0 40px {_glow(p, 0.1)};"></div>
      <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
        width:180px;height:180px;border:1px solid {p}10;border-radius:50%;"></div>
      <h2 style="position:absolute;top:40px;left:50%;transform:translateX(-50%);
        font-size:{title_size}px;font-weight:900;color:{_c('text')};
        text-shadow:0 0 20px {_glow(p)};margin:0;z-index:5;">{title}</h2>
      {corner_html}
      {center}
    </div>'''


def template_list_alert(title: str, subtitle: str, items: list,
                        scene_id: int = 1, title_size: int = 96, **kw) -> str:
    a = _accent(scene_id)
    p, s = a["p"], a["s"]

    items_html = ""
    for i, item in enumerate(items[:4]):
        color = p if i % 2 == 0 else s
        icon = item.get("icon", "•")
        bar_pct = item.get("bar_pct", 60 + i * 8)
        items_html += f'''<div class="item" style="display:flex;align-items:center;gap:16px;
          padding:16px 20px;background:{color}06;border:1px solid {color}15;
          border-radius:12px;backdrop-filter:blur(8px);">
          <div style="font-size:32px;width:48px;height:48px;display:flex;align-items:center;
            justify-content:center;background:{color}15;border-radius:10px;">{icon}</div>
          <div style="flex:1;">
            <div style="font-size:22px;font-weight:700;color:{_c('text')};">{item.get("heading","")}</div>
            <div style="font-size:14px;color:{_c('text_secondary')};margin-top:4px;">{item.get("desc","")}</div>
          </div>
          <div style="width:120px;text-align:right;">
            <div style="font-size:20px;font-weight:800;color:{color};text-shadow:0 0 10px {_glow(color, 0.4)};">{bar_pct}%</div>
            <div style="width:100%;height:4px;background:rgba(255,255,255,0.06);border-radius:2px;margin-top:6px;">
              <div style="width:{bar_pct}%;height:100%;background:linear-gradient(90deg,{color},{_c('data')});
                border-radius:2px;"></div>
            </div>
          </div>
        </div>'''

    return f'''<div class="scene-content" style="display:flex;flex-direction:column;width:100%;height:100%;
      padding:60px 100px;box-sizing:border-box;gap:16px;font-family:'Inter','Noto Sans SC',sans-serif;">
      {_grid_overlay(p)}
      {_ghost_text("LIST", s)}
      <div style="text-align:center;position:relative;z-index:2;">
        <h2 style="font-size:{title_size}px;font-weight:900;color:{_c('text')};
          text-shadow:0 0 20px {_glow(p)};margin:0;">{title}</h2>
        <p class="subtitle" style="font-size:16px;color:{_c('text_secondary')};margin:8px 0 0 0;">{subtitle}</p>
        {_divider(p)}
      </div>
      <div style="display:flex;flex-direction:column;gap:12px;flex:1;justify-content:center;
        position:relative;z-index:2;">{items_html}</div>
    </div>'''


def template_flow(title: str, steps: list, subtitle: str = "",
                  scene_id: int = 1, title_size: int = 96, **kw) -> str:
    a = _accent(scene_id)
    p, s = a["p"], a["s"]

    parts = []
    for i, step in enumerate(steps[:4]):
        color = p if i % 2 == 0 else s
        label = step.get("label", "")
        desc = step.get("desc", "")
        parts.append(f'''<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:12px;">
          <div style="width:52px;height:52px;border-radius:50%;background:{color}20;
            border:2px solid {color};display:flex;align-items:center;justify-content:center;
            font-size:22px;font-weight:900;color:{color};
            box-shadow:0 0 20px {_glow(color, 0.4)};">{i+1}</div>
          <div class="item" style="background:{color}08;border:1px solid {color}20;border-radius:12px;
            padding:20px;text-align:center;width:100%;backdrop-filter:blur(8px);">
            <div style="font-size:22px;font-weight:700;color:{color};">{label}</div>
            <div style="font-size:14px;color:{_c('text_secondary')};margin-top:8px;">{desc}</div>
          </div>
        </div>''')
        if i < len(steps[:4]) - 1:
            parts.append(f'''<div style="display:flex;align-items:center;padding-top:20px;">
              <div style="width:30px;height:2px;background:linear-gradient(90deg,{p},{s});"></div>
              <div style="width:0;height:0;border-top:5px solid transparent;
                border-bottom:5px solid transparent;border-left:7px solid {s};"></div>
            </div>''')

    return f'''<div class="scene-content" style="display:flex;flex-direction:column;width:100%;height:100%;
      padding:60px 80px;box-sizing:border-box;gap:20px;justify-content:center;
      font-family:'Inter','Noto Sans SC',sans-serif;">
      {_grid_overlay(p)}
      {_ghost_text("FLOW", p)}
      <h1 style="font-size:{title_size}px;font-weight:900;color:{_c('text')};text-align:center;
        text-shadow:0 0 20px {_glow(p)};margin:0;position:relative;z-index:2;">{title}</h1>
      <div style="display:flex;align-items:flex-start;gap:8px;flex:1;position:relative;z-index:2;">{''.join(parts)}</div>
      <p class="subtitle" style="font-size:16px;color:{_c('text_secondary')};text-align:center;
        position:relative;z-index:2;">{subtitle}</p>
    </div>'''


# ============================================================
# 模板映射
# ============================================================
TEMPLATES = {
    "data_impact": template_data_impact,
    "dashboard": template_dashboard,
    "compare": template_compare,
    "quote_hero": template_quote_hero,
    "hud": template_hud,
    "list_alert": template_list_alert,
    "flow": template_flow,
}
