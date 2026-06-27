#!/usr/bin/env python3
"""
taste_inject.py — design-taste 知识注入器 (V1.0)

从 E:/Hermes-Agent/skills/design-taste/references/ 读取品味约束，
注入到 hf_builder / design_system / quality_checker 的 prompt 中。
pipeline 不动，skill 不动，只改注入数据。
"""
import re
from pathlib import Path

# design-taste skill 路径
_TASTE_SKILL_DIR = Path(r"E:\Hermes-Agent\skills\design-taste")


# ── 场景品味卡 ──────────────────────────────────────────

def get_taste_card(visual_type: str) -> str:
    """按 visual_type 加载品味卡。"""
    path = _TASTE_SKILL_DIR / "references" / "visual-type-cards.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    pattern = rf"## {re.escape(visual_type)}.*?(?=\n## |\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(0).strip() if m else ""


# ── 反模式禁令 ──────────────────────────────────────────

def get_anti_patterns(design_style: str = "") -> str:
    """加载反模式目录。按风格过滤专属禁令。"""
    path = _TASTE_SKILL_DIR / "references" / "anti-patterns-catalog.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    result = []
    in_style = False
    sk = design_style.lower().replace(" ", "") if design_style else ""

    for line in lines:
        # 风格专属段检测
        if line.startswith("### "):
            style_words = line[4:].lower().replace(" ", "").replace("(", "").replace(")", "")
            in_style = bool(sk) and sk in style_words
        if not line.startswith("### "):
            if in_style or not line.startswith("## "):
                result.append(line)
    return "\n".join(result)


# ── 动画模式 ────────────────────────────────────────────

def get_animation_patterns() -> str:
    """加载动画模式库（截取核心部分）。"""
    path = _TASTE_SKILL_DIR / "references" / "animation-patterns.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")[:2500]


# ── 设计 token ──────────────────────────────────────────

def get_design_tokens() -> str:
    """加载设计 token 系统（用于 design_system 注入）。"""
    path = _TASTE_SKILL_DIR / "references" / "design-tokens.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


# ── Pre-flight checklist ─────────────────────────────────

def get_preflight_checklist() -> str:
    """加载品味 pre-flight checklist（用于 quality_checker 注入）。"""
    path = _TASTE_SKILL_DIR / "references" / "pre-flight-checklist.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


# ── 整合注入 ────────────────────────────────────────────

def get_scene_taste_injection(scene: dict, design_style: str = "") -> str:
    """一次性获取场景品味约束（用于 hf_builder prompt 拼接）。"""
    parts = []
    vt = scene.get("visual_type", "")
    if vt:
        card = get_taste_card(vt)
        if card:
            parts.append(f"## 🎨 场景品味约束 (design-taste V1.0)\n{card}")
    ap = get_anti_patterns(design_style)
    if ap:
        parts.append(f"## 🚫 反模式禁令\n{ap[:1500]}")
    if not parts:
        return ""
    return "\n\n<!-- design-taste V1.0 injection -->\n\n" + "\n\n".join(parts)
