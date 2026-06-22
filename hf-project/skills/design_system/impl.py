"""
design_system/impl.py - 视觉系统生成器 v3
支持多种预设风格：cyber_tech, apple_keynote, luxury_dark, data_viz
"""

import os, json, re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from llm_utils import call_llm

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
DESIGN_PATH = OUTPUT_DIR / "design.md"

LLM_CONFIGS = [
    {"name":"mimo","url":"https://token-plan-cn.xiaomimimo.com/v1/chat/completions","model":"mimo-v2.5-pro","env_key":"XIAOMI_API_KEY"},
    {"name":"deepseek","url":"https://api.deepseek.com/v1/chat/completions","model":"deepseek-chat","env_key":"DEEPSEEK_API_KEY"},
]
PRESET_STYLES = {
    "cyber_tech": {
        "name": "赛博朋克科技风",
        "description": "深黑背景+霓虹发光，科技暗黑风格",
        "mood": "科技感、未来感、冲击力",
        "best_for": "科技、AI、互联网、数码",
        "colors": {"background":"#0a0a0a","primary":"#00D4FF","accent":"#FF4081","data":"#FFD700","text":"#FFFFFF","text_secondary":"#999999"},
        "typography": {
            "headline": {"fontFamily":"Noto Sans SC, PingFang SC","fontSize":"72-120px","fontWeight":"bold"},
            "body": {"fontFamily":"Noto Sans SC, PingFang SC","fontSize":"28-36px","fontWeight":"regular"},
            "data": {"fontFamily":"JetBrains Mono, monospace","fontSize":"48-80px","fontWeight":"bold"},
        },
        "spacing": {"scene_padding":"80-120px","element_gap":"24-40px","card_radius":"16px"},
        "motion": {"energy":"high","entry_easing":"expo.out","exit_easing":"power4.in"},
        "atmosphere": ["radial-glow","data-grid","neon-lines","particle-drift","ghost-text"],
        "donts": ["明亮自然色彩","卡通化元素","font-size低于24px","纯色平面背景","居中浮动布局"],
    },
    "apple_keynote": {
        "name": "苹果发布会风",
        "description": "简洁+冲击力+留白",
        "mood": "高端、简洁、震撼",
        "best_for": "产品发布、品牌宣传",
        "colors": {"background":"#000000","primary":"#FFFFFF","accent":"#0071E3","data":"#30D158","text":"#FFFFFF","text_secondary":"#86868B"},
        "typography": {
            "headline": {"fontFamily":"SF Pro Display, PingFang SC","fontSize":"96-160px","fontWeight":"bold"},
            "body": {"fontFamily":"SF Pro Text, PingFang SC","fontSize":"32-42px","fontWeight":"regular"},
            "data": {"fontFamily":"SF Pro Display, monospace","fontSize":"64-120px","fontWeight":"bold"},
        },
        "spacing": {"scene_padding":"120-200px","element_gap":"40-60px","card_radius":"20px"},
        "motion": {"energy":"medium","entry_easing":"power3.out","exit_easing":"power2.in"},
        "atmosphere": ["subtle-gradient","soft-glow","minimal-lines"],
        "donts": ["过度装饰","太多颜色","复杂布局"],
    },
    "luxury_dark": {
        "name": "奢华暗黑风",
        "description": "高端暗黑风格，金色点缀",
        "mood": "高端、永恒、奢华",
        "best_for": "金融、奢侈品、高端品牌",
        "colors": {"background":"#0a0a0a","primary":"#C9A96E","accent":"#FFFFFF","data":"#C9A96E","text":"#FFFFFF","text_secondary":"#666666"},
        "typography": {
            "headline": {"fontFamily":"Noto Serif SC, PingFang SC","fontSize":"72-120px","fontWeight":"bold"},
            "body": {"fontFamily":"Noto Sans SC, PingFang SC","fontSize":"28-36px","fontWeight":"regular"},
            "data": {"fontFamily":"JetBrains Mono, monospace","fontSize":"48-80px","fontWeight":"bold"},
        },
        "spacing": {"scene_padding":"100-160px","element_gap":"32-48px","card_radius":"12px"},
        "motion": {"energy":"low","entry_easing":"power2.out","exit_easing":"power2.in"},
        "atmosphere": ["gold-shimmer","dark-texture","subtle-pattern"],
        "donts": ["明亮色彩","卡通元素","快速动画"],
    },
    "data_viz": {
        "name": "数据可视化风",
        "description": "清晰、专业、数据驱动",
        "mood": "专业、清晰、可信",
        "best_for": "数据分析、报告、统计",
        "colors": {"background":"#1a1a2e","primary":"#00D4FF","accent":"#FF6B6B","data":"#4ECDC4","text":"#FFFFFF","text_secondary":"#A0A0B0"},
        "typography": {
            "headline": {"fontFamily":"Inter, Noto Sans SC","fontSize":"64-96px","fontWeight":"bold"},
            "body": {"fontFamily":"Inter, Noto Sans SC","fontSize":"24-32px","fontWeight":"regular"},
            "data": {"fontFamily":"JetBrains Mono, monospace","fontSize":"48-72px","fontWeight":"bold"},
        },
        "spacing": {"scene_padding":"60-100px","element_gap":"20-32px","card_radius":"12px"},
        "motion": {"energy":"medium","entry_easing":"power3.out","exit_easing":"power2.in"},
        "atmosphere": ["grid-lines","data-charts","progress-bars","metric-cards"],
        "donts": ["过于花哨","无关装饰","复杂动画"],
    },
}




def select_style_for_topic(topic):
    t = (topic or "").lower()
    if any(k in t for k in ["ai","人工智能","agent","科技","技术","互联网","数码"]):
        return "cyber_tech"
    elif any(k in t for k in ["发布","新品","苹果","产品","品牌"]):
        return "apple_keynote"
    elif any(k in t for k in ["金融","投资","奢侈","高端"]):
        return "luxury_dark"
    elif any(k in t for k in ["数据","统计","分析","报告"]):
        return "data_viz"
    return "cyber_tech"

def generate_scene_variants_fallback(topic, style):
    """Fallback场景变体（当LLM失败时使用）"""
    colors = style["colors"]
    return f"""
### Opening（开场画面）
- 背景层：深黑背景({colors["background"]}) + 径向光晕({colors["primary"]} 15%透明度)
- 中景层：大标题(72-120px) + 副标题(36-48px)，填满画面60-80%
- 前景层：霓虹线条装饰 + 数据网格
- 动画：标题SLAMS IN from left，副标题CASCADE IN staggered 0.2s
- 密度：8-10个视觉元素

### Data（数据展示）
- 背景层：数据网格背景 + 流光效果
- 中景层：大数字(48-80px {colors["data"]}) + 趋势箭头 + 进度条
- 前景层：标签(18-24px) + 装饰线条
- 动画：数字COUNTS UP，箭头SLIDES IN
- 密度：9个视觉元素

### Comparison（对比展示）
- 背景层：分屏背景（左暗右亮）
- 中景层：左右对比面板 + VS分割线
- 前景层：高亮标签 + 装饰光晕
- 动画：左面板SLIDES LEFT，右面板SLIDES RIGHT
- 密度：8个视觉元素

### Quote（金句/引用）
- 背景层：深黑 + 大字幽灵文字(ghost-text)
- 中景层：金句大字(72-120px {colors["primary"]}) + 引号装饰
- 前景层：发光线条 + 粒子漂移
- 动画：文字FLOATS IN gently，装饰PULSES
- 密度：8个视觉元素

### Closing（收尾画面）
- 背景层：渐变光晕 + 总结性视觉
- 中景层：总结标题 + CTA按钮
- 前景层：品牌标识 + 装饰收尾
- 动画：标题SOLIDIFIES IN，CTABOUNCES
- 密度：8-10个视觉元素
"""

def generate_scene_variants(topic, style):
    colors = style["colors"]
    sys_p = "你是专业的视频视觉设计师。生成5个场景变体设计指导。输出纯文本markdown。"
    p = f"""话题: {topic}
风格: {style["name"]} ({style["mood"]})
配色: 背景{colors["background"]}, 主色{colors["primary"]}, 强调{colors["accent"]}

生成5个场景变体：opening/data/comparison/quote/closing
每个需要背景层、中景层（填满60-80%）、前景层、动画、密度（8-10元素）"""
    result = call_llm(p, sys_p, max_tokens=4000)
    if not result or len(result) < 100:
        print("  [design-system] LLM场景变体生成失败，使用fallback")
        return generate_scene_variants_fallback(topic, style)
    return result

def generate_design_md(topic, style_key="auto", scene_variants=""):
    if style_key=="auto":
        style_key = select_style_for_topic(topic)
    style = PRESET_STYLES.get(style_key, PRESET_STYLES["cyber_tech"])
    c = style["colors"]; t = style["typography"]; s = style["spacing"]; m = style["motion"]; a = style["atmosphere"]; d = style["donts"]

    yf = f"""---
name: {style["name"]}
style_key: {style_key}
description: {style["description"]}
colors:
  background: "{c["background"]}"
  primary: "{c["primary"]}"
  accent: "{c["accent"]}"
  data: "{c["data"]}"
  text: "{c["text"]}"
  text_secondary: "{c["text_secondary"]}"
typography:
  headline:
    fontFamily: "{t["headline"]["fontFamily"]}"
    fontSize: "{t["headline"]["fontSize"]}"
    fontWeight: {t["headline"]["fontWeight"]}
  body:
    fontFamily: "{t["body"]["fontFamily"]}"
    fontSize: "{t["body"]["fontSize"]}"
    fontWeight: {t["body"]["fontWeight"]}
  data:
    fontFamily: "{t["data"]["fontFamily"]}"
    fontSize: "{t["data"]["fontSize"]}"
    fontWeight: {t["data"]["fontWeight"]}
rounded:
  sm: {s["card_radius"]}
  md: {int(s["card_radius"].replace("px",""))+8}px
spacing:
  scene_padding: "{s["scene_padding"]}"
  element_gap: "{s["element_gap"]}"
  card_radius: "{s["card_radius"]}"
motion:
  energy: {m["energy"]}
  easing:
    entry: "{m["entry_easing"]}"
    exit: "{m["exit_easing"]}"
  atmosphere: {json.dumps(a)}
---"""

    pr = f"""
## Overview

{topic} -- 采用{style["name"]}视觉风格，{style["mood"]}调性。

**视觉隐喻**: {style["description"]}

**情绪关键词**: {style["mood"]}

**最适合**: {style["best_for"]}

## Colors

| 用途 | 颜色 | Hex |
|------|------|-----|
| 背景 | 主背景 | {c["background"]} |
| 主色 | 标题/强调 | {c["primary"]} |
| 强调 | 高亮/CTA | {c["accent"]} |
| 数据 | 数字/图表 | {c["data"]} |
| 文字 | 主要文字 | {c["text"]} |

## Typography

| 层级 | 字体 | 大小 | 重量 |
|------|------|------|------|
| 标题 | {t["headline"]["fontFamily"].split(",")[0]} | {t["headline"]["fontSize"]} | {t["headline"]["fontWeight"]} |
| 正文 | {t["body"]["fontFamily"].split(",")[0]} | {t["body"]["fontSize"]} | {t["body"]["fontWeight"]} |
| 数据 | {t["data"]["fontFamily"].split(",")[0]} | {t["data"]["fontSize"]} | {t["data"]["fontWeight"]} |

## 视觉层次

每个场景必须包含3层：

1. **背景层**: {", ".join(a[:3])}
2. **中景层**: 核心内容 -- 必须填满画面60-80%
3. **前景层**: {", ".join(a[3:]) if len(a)>3 else a[-1]}

## 装饰元素

{chr(10).join(f"- {x}" for x in a)}

## 场景变体

{scene_variants if scene_variants else "等待LLM生成..."}

## Density

- 每个场景 **8-10个视觉元素**
- 至少2个装饰元素是主动添加的

## Scale

- 标题: {t["headline"]["fontSize"]}，占画面宽度60-80%
- 正文: {t["body"]["fontSize"]}
- 数据: {t["data"]["fontSize"]}
- 装饰透明度: 15-25%
- 边框: 2-4px

## Don'ts

{chr(10).join(f"- {x}" for x in d)}

---

*风格由design-system skill自动生成，visual-author必须遵循以上约束。*
"""
    return yf + pr, style_key

def run(context):
    topic = context.get("topic", "未知话题")
    style_key = context.get("style_key", "auto")
    print(f"  [design-system] 为 '{topic}' 生成视觉系统...")
    if style_key=="auto":
        style_key = select_style_for_topic(topic)
    style = PRESET_STYLES.get(style_key, PRESET_STYLES["cyber_tech"])
    print(f"  [design-system] 风格: {style['name']} ({style_key})")
    sv = generate_scene_variants(topic, style)
    if sv:
        print(f"  [design-system] 生成场景变体: {len(sv)} 字符")
    dm, used = generate_design_md(topic, style_key, sv)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(DESIGN_PATH, "w", encoding="utf-8") as f:
        f.write(dm)
    print(f"  [design-system] 已保存到: {DESIGN_PATH}")
    context["design_md_path"] = str(DESIGN_PATH)
    context["design_style"] = style["name"]
    context["design_style_key"] = used
    return context

if __name__=="__main__":
    import json as _json
    # 从 topic_selected.json 读取话题
    selected_path = Path(__file__).parent.parent.parent / "output" / "topic_selected.json"
    topic = "未知话题"
    if selected_path.exists():
        with open(selected_path, encoding="utf-8") as _f:
            _d = _json.load(_f)
        topic = _d.get("topic") or _d.get("selected_topic", "未知话题")
    ctx = {"topic": topic}
    r = run(ctx)
    print(f"  结果: {r.get('design_style')}")
