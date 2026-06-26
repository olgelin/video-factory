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
    # 官方8种风格（来自HyperFrames visual-styles.md）
    "swiss_pulse": {
        "name": "Swiss Pulse",
        "description": "Grid-locked compositions, clinical precision",
        "mood": "Clinical, precise",
        "best_for": "SaaS, data, dev tools, metrics",
        "colors": {"background":"#1a1a1a","primary":"#ffffff","accent":"#0066FF","data":"#0066FF","text":"#ffffff","text_secondary":"#999999"},
        "typography": {
            "headline": {"fontFamily":"Helvetica Neue","fontSize":"80-120px","fontWeight":"700"},
            "body": {"fontFamily":"Inter","fontSize":"14px","fontWeight":"400"},
            "data": {"fontFamily":"Helvetica Neue","fontSize":"112px","fontWeight":"700"},
        },
        "spacing": {"scene_padding":"32px","element_gap":"16px","card_radius":"2px"},
        "motion": {"energy":"high","entry_easing":"expo.out","exit_easing":"power4.in"},
        "atmosphere": ["grid-lines","registration-marks"],
        "donts": ["floating elements","decorative transitions","soft shadows"],
    },
    "velvet_standard": {
        "name": "Velvet Standard",
        "description": "Premium, timeless, generous negative space",
        "mood": "Premium, timeless",
        "best_for": "Luxury products, enterprise, keynotes",
        "colors": {"background":"#0a0a0a","primary":"#ffffff","accent":"#1a237e","data":"#1a237e","text":"#ffffff","text_secondary":"#999999"},
        "typography": {
            "headline": {"fontFamily":"Inter","fontSize":"48px","fontWeight":"300","letterSpacing":"0.15em","textTransform":"uppercase"},
            "body": {"fontFamily":"Inter","fontSize":"16px","fontWeight":"300","lineHeight":"1.6"},
            "data": {"fontFamily":"Inter","fontSize":"48px","fontWeight":"300"},
        },
        "spacing": {"scene_padding":"64px","element_gap":"32px","card_radius":"2px"},
        "motion": {"energy":"calm","entry_easing":"sine.inOut","exit_easing":"power1.in"},
        "atmosphere": ["subtle-grain","hairline-rules"],
        "donts": ["sharp snaps","fast transitions","heavy shadows"],
    },
    "deconstructed": {
        "name": "Deconstructed",
        "description": "Industrial, raw, gritty textures",
        "mood": "Industrial, raw",
        "best_for": "Tech launches, security, punk",
        "colors": {"background":"#1a1a1a","primary":"#f0f0f0","accent":"#D4501E","data":"#D4501E","text":"#f0f0f0","text_secondary":"#999999"},
        "typography": {
            "headline": {"fontFamily":"Space Grotesk","fontSize":"64px","fontWeight":"700"},
            "body": {"fontFamily":"Space Mono","fontSize":"12px","fontWeight":"700","textTransform":"uppercase"},
            "data": {"fontFamily":"Space Grotesk","fontSize":"64px","fontWeight":"700"},
        },
        "spacing": {"scene_padding":"24px","element_gap":"12px","card_radius":"0px"},
        "motion": {"energy":"high","entry_easing":"back.out(2.5)","exit_easing":"steps(8)"},
        "atmosphere": ["scan-lines","glitch-artifacts","grain-overlay"],
        "donts": ["polished surfaces","symmetrical layouts","smooth gradients"],
    },
    "maximalist_type": {
        "name": "Maximalist Type",
        "description": "Text IS the visual, overlapping type layers",
        "mood": "Loud, kinetic",
        "best_for": "Big announcements, launches",
        "colors": {"background":"#0a0a0a","primary":"#ffffff","accent":"#E63946","data":"#FFD60A","text":"#ffffff","text_secondary":"#999999"},
        "typography": {
            "headline": {"fontFamily":"Anton","fontSize":"128px","fontWeight":"400","textTransform":"uppercase"},
            "body": {"fontFamily":"Space Grotesk","fontSize":"48px","fontWeight":"700"},
            "data": {"fontFamily":"Anton","fontSize":"128px","fontWeight":"400"},
        },
        "spacing": {"scene_padding":"0px","element_gap":"8px","card_radius":"0px"},
        "motion": {"energy":"high","entry_easing":"expo.out","exit_easing":"back.out(1.8)"},
        "atmosphere": ["type-layers","color-blocks"],
        "donts": ["static moments","negative space","subtle animations"],
    },
    "data_drift": {
        "name": "Data Drift",
        "description": "Futuristic, immersive, fluid morphing",
        "mood": "Futuristic, immersive",
        "best_for": "AI, ML, cutting-edge tech",
        "colors": {"background":"#0a0a0a","primary":"#e0e0e0","accent":"#7c3aed","data":"#06b6d4","text":"#e0e0e0","text_secondary":"#999999"},
        "typography": {
            "headline": {"fontFamily":"Inter","fontSize":"40px","fontWeight":"200","letterSpacing":"0.05em"},
            "body": {"fontFamily":"Inter","fontSize":"14px","fontWeight":"300"},
            "data": {"fontFamily":"Inter","fontSize":"40px","fontWeight":"200"},
        },
        "spacing": {"scene_padding":"64px","element_gap":"32px","card_radius":"9999px"},
        "motion": {"energy":"moderate","entry_easing":"sine.inOut","exit_easing":"power2.out"},
        "atmosphere": ["particle-field","light-traces","radial-glow"],
        "donts": ["hard edges","sharp transitions","heavy text"],
    },
    "soft_signal": {
        "name": "Soft Signal",
        "description": "Intimate, warm, personal",
        "mood": "Intimate, warm",
        "best_for": "Wellness, personal stories, brand",
        "colors": {"background":"#FFF8EC","primary":"#2a2a2a","accent":"#F5A623","data":"#C4A3A3","text":"#2a2a2a","text_secondary":"#999999"},
        "typography": {
            "headline": {"fontFamily":"Playfair Display","fontSize":"48px","fontWeight":"400","fontStyle":"italic"},
            "body": {"fontFamily":"Inter","fontSize":"16px","fontWeight":"300","lineHeight":"1.7"},
            "data": {"fontFamily":"Playfair Display","fontSize":"48px","fontWeight":"400"},
        },
        "spacing": {"scene_padding":"48px","element_gap":"24px","card_radius":"9999px"},
        "motion": {"energy":"calm","entry_easing":"sine.inOut","exit_easing":"power1.inOut"},
        "atmosphere": ["soft-gradient","warm-grain"],
        "donts": ["hurried motion","polished surfaces","corporate feel"],
    },
    "folk_frequency": {
        "name": "Folk Frequency",
        "description": "Cultural, vivid, handcrafted",
        "mood": "Cultural, vivid",
        "best_for": "Consumer apps, food, communities",
        "colors": {"background":"#ffffff","primary":"#1a1a1a","accent":"#FF1493","data":"#0047AB","text":"#1a1a1a","text_secondary":"#999999"},
        "typography": {
            "headline": {"fontFamily":"Fredoka One","fontSize":"64px","fontWeight":"400"},
            "body": {"fontFamily":"Nunito","fontSize":"16px","fontWeight":"600"},
            "data": {"fontFamily":"Fredoka One","fontSize":"64px","fontWeight":"400"},
        },
        "spacing": {"scene_padding":"32px","element_gap":"16px","card_radius":"9999px"},
        "motion": {"energy":"high","entry_easing":"back.out(1.6)","exit_easing":"elastic.out(1, 0.5)"},
        "atmosphere": ["pattern-tiles","confetti-burst","color-blocks"],
        "donts": ["minimalist design","muted colors","subtle motion"],
    },
    "shadow_cut": {
        "name": "Shadow Cut",
        "description": "Dark, cinematic, dramatic reveals",
        "mood": "Dark, cinematic",
        "best_for": "Dramatic reveals, security, exposé",
        "colors": {"background":"#0a0a0a","primary":"#f0f0f0","accent":"#C1121F","data":"#C1121F","text":"#f0f0f0","text_secondary":"#999999"},
        "typography": {
            "headline": {"fontFamily":"Oswald","fontSize":"64px","fontWeight":"700","textTransform":"uppercase"},
            "body": {"fontFamily":"Inter","fontSize":"14px","fontWeight":"400"},
            "data": {"fontFamily":"Oswald","fontSize":"64px","fontWeight":"700"},
        },
        "spacing": {"scene_padding":"48px","element_gap":"16px","card_radius":"2px"},
        "motion": {"energy":"moderate","entry_easing":"power3.out","exit_easing":"power4.in"},
        "atmosphere": ["deep-shadow","vignette","grain-overlay"],
        "donts": ["bright colors","soft edges","fast cuts"],
    },
}




def select_style_for_topic(topic, emotion_arc=""):
    """根据情绪弧线选择视觉风格（优先），关键词匹配兜底"""
    # 1. 情绪驱动选择（优先）
    if emotion_arc:
        ea = emotion_arc.lower()
        # 压抑/黑暗/悲剧 → shadow_cut
        if any(k in ea for k in ["压抑", "黑暗", "悲剧", "沉重", "痛苦", "悲伤"]):
            return "shadow_cut"
        # 爆发/愤怒/震撼 → maximalist_type
        if any(k in ea for k in ["爆发", "愤怒", "震撼", "激烈", "冲突", "对抗"]):
            return "maximalist_type"
        # 升华/温暖/希望 → soft_signal
        if any(k in ea for k in ["升华", "温暖", "希望", "反思", "思考", "感悟"]):
            return "soft_signal"
        # 冷静/理性/分析 → swiss_pulse
        if any(k in ea for k in ["冷静", "理性", "分析", "数据", "逻辑"]):
            return "swiss_pulse"
        # 叙事/故事/情感 → velvet_standard
        if any(k in ea for k in ["叙事", "故事", "情感", "人物"]):
            return "velvet_standard"
        # 混合情绪（如"压抑→爆发→升华"）→ shadow_cut（最匹配戏剧性）
        if "→" in emotion_arc or "—" in emotion_arc:
            return "shadow_cut"
    
    # 2. 关键词匹配兜底
    t = (topic or "").lower()
    # 官方风格映射（基于Mood → Style Guide）
    if any(k in t for k in ["数据","分析","统计","报告","指标","dashboard"]):
        return "swiss_pulse"
    elif any(k in t for k in ["高端","奢侈","金融","投资","企业","品牌"]):
        return "velvet_standard"
    elif any(k in t for k in ["科技","技术","安全","开源","punk","工业"]):
        return "deconstructed"
    elif any(k in t for k in ["发布","新品","宣布","launch","hype"]):
        return "maximalist_type"
    elif any(k in t for k in ["ai","人工智能","ml","机器学习","未来","futuristic"]):
        return "data_drift"
    elif any(k in t for k in ["健康","生活","个人","故事","温暖","wellness"]):
        return "soft_signal"
    elif any(k in t for k in ["文化","美食","社区","节日","consumer"]):
        return "folk_frequency"
    elif any(k in t for k in ["戏剧","揭秘","安全","黑暗","cinematic"]):
        return "shadow_cut"
    # 原有风格映射
    if any(k in t for k in ["ai","人工智能","agent","科技","技术","互联网","数码"]):
        return "cyber_tech"
    elif any(k in t for k in ["发布","新品","苹果","产品","品牌"]):
        return "apple_keynote"
    elif any(k in t for k in ["金融","投资","奢侈","高端"]):
        return "luxury_dark"
    elif any(k in t for k in ["数据","统计","分析","报告"]):
        return "data_viz"
    # 默认：根据情绪选择
    return "swiss_pulse"  # 默认使用Swiss Pulse（最通用）

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
    
    # 从 topic_selected.json 读取 emotion_arc
    emotion_arc = ""
    topic_selected_path = OUTPUT_DIR / "topic_selected.json"
    if topic_selected_path.exists():
        try:
            with open(topic_selected_path, "r", encoding="utf-8") as f:
                ts = json.load(f)
            emotion_arc = ts.get("emotion_arc", "")
        except Exception:
            pass
    
    print(f"  [design-system] 为 '{topic}' 生成视觉系统...")
    if style_key=="auto":
        style_key = select_style_for_topic(topic, emotion_arc)
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

    # === V4新增：生成design_specs.json（hf_builder需要）===
    c = style["colors"]; t = style["typography"]; m = style["motion"]
    specs = []
    # 动态场景类型：根据storyboard场景数生成
    scene_types = ["opening", "data", "comparison", "quote", "flow", "timeline", "hud", "closing"]
    # 读取storyboard获取实际场景数
    storyboard_path = OUTPUT_DIR / "storyboard.json"
    num_scenes = 8  # 默认
    if storyboard_path.exists():
        try:
            with open(storyboard_path, "r", encoding="utf-8") as f:
                sb = json.load(f)
            scenes = sb if isinstance(sb, list) else sb.get("scenes", [])
            num_scenes = len(scenes)
        except Exception:
            pass
    
    for i in range(num_scenes):
        st = scene_types[i % len(scene_types)]
        energy = m["energy"]
        # 根据场景类型调整energy
        if st in ["opening", "data", "comparison"]:
            energy = "high" if st == "data" else m["energy"]
        elif st in ["quote", "closing"]:
            energy = "calm"
        specs.append({
            "scene_id": i + 1,
            "scene_type": st,
            "colors": c,
            "typography": t,
            "motion": m,
            "energy": energy,
        })
    specs_path = OUTPUT_DIR / "design_specs.json"
    with open(specs_path, "w", encoding="utf-8") as f:
        json.dump(specs, f, ensure_ascii=False, indent=2)
    print(f"  [design-system] 已保存specs: {specs_path} ({len(specs)}个场景)")

    context["design_md_path"] = str(DESIGN_PATH)
    context["design_specs_path"] = str(specs_path)
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
