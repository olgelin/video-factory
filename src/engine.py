#!/usr/bin/env python3
"""
V18 Engine — 细分化模板系统 + Apple科技赛博风格

核心理念：
  不是完全自由的LLM设计（太不稳定）
  不是固定的12模板（太套壳）
  而是"细分化的模板系统" — LLM在约束框架内创意设计

设计锁定：
  - 配色：Apple科技感（深蓝/深灰+青色/白色+少量警示色）
  - 背景：4种高质量模板（粒子科技/极简渐变/几何线条/微光效果）
  - 布局：6种创意布局（diagonal/asymmetric/split_h/dashboard/timeline/full_bleed）
  - 卡片：统一风格（边框+半透明背景+圆角）
  - 动画：统一入场（fade_up/scale_in）+ 呼吸感

解决的问题：
  1. 风格low → 锁定Apple科技赛博风格
  2. 下面200px空白 → 数据区域强制占满画面
  3. 内容割裂 → 无法可视化的数据用卡片形式
  4. 背景复杂 → 锁定4种高质量背景模板
"""

import os
import sys
import json
import re
import math
import requests
from pathlib import Path
from typing import Optional

# ============================================================
# LLM API — 统一走 provider.py
# ============================================================
import sys
from pathlib import Path
_provider_dir = Path(__file__).parent.parent / "hf-project"
if str(_provider_dir) not in sys.path:
    sys.path.insert(0, str(_provider_dir))
from provider import call_llm as _provider_call_llm

def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 4000, max_retries: int = 3) -> str:
    """调用 LLM，统一走 provider.py（DeepSeek 官方 API）"""
    return _provider_call_llm(prompt, system_prompt, max_tokens, timeout=120)


def extract_json(text: str) -> Optional[list | dict]:
    """Extract JSON from LLM response with multiple fallback strategies."""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for start_char, end_char in [('[', ']'), ('{', '}')]:
        start = text.find(start_char)
        if start >= 0:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == start_char:
                    depth += 1
                elif text[i] == end_char:
                    depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        break
    return None


# ============================================================
# Step 1: Generate Script (口播文案)
# ============================================================

def generate_script(topic: str) -> list[dict]:
    """Generate a 6-scene script for the topic."""
    prompt = f"""你是一个顶级短视频口播文案大师。为话题「{topic}」写一个6场景的口播脚本。

要求：
1. 每个场景25-50字口播文案，口语化、有冲击力
2. 必须包含具体数字/数据/事实（不能含糊）
3. 第一个是hook（吸引注意力的数据或反常识）
4. 最后一个是金句总结
5. 内容要有层次递进，不能平铺直叙
6. 每个场景都要有独特的信息点，不能重复

输出JSON数组，每个元素：
{{
  "scene_id": 1,
  "narration": "口播文案",
  "duration": 5.0,
  "visual_type": "highlight|data|comparison|timeline|alert|modules|quote"
}}

输出纯JSON数组，不要其他文字。"""

    resp = call_llm(prompt, system_prompt="你是短视频脚本专家。只输出JSON数组，不要其他内容。", max_tokens=3000)
    scenes = extract_json(resp)

    if not isinstance(scenes, list) or len(scenes) < 4:
        print(f"  ⚠️ LLM script failed ({resp[:100]}), using backup")
        scenes = _backup_script(topic)

    for i, s in enumerate(scenes):
        s["scene_id"] = i + 1
    return scenes


def _backup_script(topic: str) -> list[dict]:
    """Backup script if LLM fails."""
    return [
        {"scene_id": 1, "narration": f"关于{topic}，有一个数据可能会颠覆你的认知。", "duration": 5.0, "visual_type": "highlight"},
        {"scene_id": 2, "narration": f"{topic}的核心数据正在发生剧烈变化。", "duration": 5.0, "visual_type": "data"},
        {"scene_id": 3, "narration": f"对比过去和现在，{topic}的变化是指数级的。", "duration": 5.0, "visual_type": "comparison"},
        {"scene_id": 4, "narration": f"这些数字背后，隐藏着一个被忽视的规律。", "duration": 5.0, "visual_type": "data"},
        {"scene_id": 5, "narration": f"但真正的关键在于，{topic}将如何改变我们的未来。", "duration": 5.0, "visual_type": "modules"},
        {"scene_id": 6, "narration": f"{topic}告诉我们：看清趋势的人，才能赢在起点。", "duration": 5.0, "visual_type": "quote"},
    ]


# ============================================================
# Step 2: Extract Storyboard Data (分镜数据)
# ============================================================

def extract_storyboard(topic: str, script_scenes: list[dict]) -> list[dict]:
    """Extract structured data for each scene."""
    narrations = "\n".join(f"场景{s['scene_id']}: {s['narration']}" for s in script_scenes)

    prompt = f"""从以下口播文案提取每个场景的结构化数据，用于视觉设计。

话题: {topic}
场景数: {len(script_scenes)}

口播文案:
{narrations}

为每个场景输出JSON数组，每个元素:
- scene_id: 场景编号
- title: 5-15字冲击力标题（必须完整，不能截断！）
- subtitle: 10-20字副标题（必须完整，不能截断！）
- key_data: 至少3个数据点，每个有 label/value/unit（必须从口播文案中提取真实数据，不能用"—"）
- key_points: 2-3个要点（每个10-20字，必须完整）
- tags: 2-3个标签
- quote_text: 如果是金句场景，提取金句

⚠️ 重要：
1. title和subtitle必须是完整的句子，不能截断！
2. key_data必须有真实的数字/数据，不能用"—"！
3. 如果口播文案没有具体数据，就从常识中补充相关数据！

输出纯JSON数组。"""

    resp = call_llm(prompt, max_tokens=4000)
    data = extract_json(resp)

    if not isinstance(data, list) or len(data) != len(script_scenes):
        print(f"  ⚠️ LLM storyboard failed, using fallback")
        data = []
        for s in script_scenes:
            data.append({
                "scene_id": s["scene_id"],
                "title": s["narration"][:15],
                "subtitle": s["narration"][15:35],
                "key_data": [{"label": "数据", "value": "—", "unit": ""}],
                "key_points": [s["narration"][:50]],
                "tags": [topic[:4]],
            })

    # 后处理：确保title和subtitle不截断
    for i, s in enumerate(data):
        title = s.get("title", "")
        subtitle = s.get("subtitle", "")
        
        # 如果title以逗号、句号结尾，去掉
        if title and title[-1] in "，。、；":
            s["title"] = title[:-1]
        
        # 如果subtitle以逗号、句号结尾，去掉
        if subtitle and subtitle[-1] in "，。、；":
            s["subtitle"] = subtitle[:-1]
        
        # 如果title太短（<5字）或太长（>20字），从key_points重新生成
        if len(title) < 5 or len(title) > 20:
            key_points = s.get("key_points", [])
            if key_points:
                # 取第一个key_points的前15字作为title
                s["title"] = key_points[0][:15]
        
        # 如果subtitle太短（<5字）或太长（>25字），从key_points重新生成
        if len(subtitle) < 5 or len(subtitle) > 25:
            key_points = s.get("key_points", [])
            if key_points and len(key_points) > 1:
                # 取第二个key_points的前20字作为subtitle
                s["subtitle"] = key_points[1][:20]
            elif key_points:
                # 取第一个key_points的15-35字作为subtitle
                s["subtitle"] = key_points[0][15:35]
        
        # 确保key_data有真实数据
        key_data = s.get("key_data", [])
        if not key_data or all(kd.get("value") == "—" for kd in key_data):
            # 从key_points中提取数据
            key_points = s.get("key_points", [])
            if key_points:
                # 尝试从key_points中提取数字
                import re
                for kp in key_points:
                    numbers = re.findall(r'\d+', kp)
                    if numbers:
                        s["key_data"] = [
                            {"label": "核心数据", "value": numbers[0], "unit": ""},
                            {"label": "关键指标", "value": numbers[1] if len(numbers) > 1 else "—", "unit": ""},
                            {"label": "参考值", "value": numbers[2] if len(numbers) > 2 else "—", "unit": ""},
                        ]
                        break

    return data


# ============================================================
# Step 3: LLM Creative Design (细分化模板系统)
# ============================================================

DESIGN_PROMPT_TEMPLATE = """你是一个顶级短视频视觉设计师。为以下{count}个场景设计视觉方案。

话题: {topic}

场景数据:
{scene_data}

## 设计约束（严格遵守！）

### 配色锁定（Apple科技赛博风格）
- 背景色：深蓝/深灰（#0a0a1a 或 #111827）
- 主强调色：科技蓝（#00d4ff 或 #3b82f6）
- 辅助色：白色（#ffffff）+ 少量警示色（橙色#ff6b35 或红色#ef4444）
- **每个场景最多3种颜色**（背景+主色+辅助色）

### 背景锁定（4种模板，选择最适合话题的）
1. **particle_tech** — 粒子科技（微粒飘浮，适合科技/未来话题）
2. **minimal_gradient** — 极简渐变（深蓝到深灰，适合通用话题）
3. **geometric_lines** — 几何线条（细线网格，适合数据/分析话题）
4. **subtle_glow** — 微光效果（柔和光晕，适合人文/社会话题）

### 布局锁定（6种创意布局，每个场景选择不同的）
1. **diagonal** — 对角线流动（标题左上→大数字右下→辅助数据分散）
2. **asymmetric** — 左右不对称分割（60/40或40/60）
3. **split_h** — 水平分割（上半标题+大数字，下半数据卡片）
4. **dashboard** — 仪表盘式（多卡片网格，但不是标准网格，要有错位）
5. **timeline** — 时间轴式（元素沿水平线分布）
6. **full_bleed** — 全画面填充（大数字占据60%画面，辅助数据四角）

### 数据可视化规则
- **可可视化的数据**：用进度条/环形图/柱状图/仪表盘
- **不可可视化的数据**：用卡片形式（边框+半透明背景+圆角）
- **每个场景至少2个卡片** — 用于展示文字信息、要点、标签等
- **卡片样式统一**：border:1px solid rgba(255,255,255,0.1), background:rgba(255,255,255,0.05), border-radius:12px

### 布局要求（关键！）
- **数据区域必须占满画面** — 不能下面留200px空白！
- **y坐标范围**：从20%到90%（不是20%到70%）
- **每个场景4-6个元素**（包括数据可视化+卡片）
- **不允许连续2个场景用同一个布局类型**

## 输出格式
每个场景输出一个JSON对象:

```
{{
  "scene_id": 1,
  "bg": {{
    "type": "particle_tech|minimal_gradient|geometric_lines|subtle_glow",
    "color": "#0a1a2e"
  }},
  "layout": {{
    "type": "diagonal|asymmetric|split_h|dashboard|timeline|full_bleed"
  }},
  "title": {{
    "text": "视觉标题",
    "size": 48,
    "color": "#ffffff",
    "weight": 900
  }},
  "subtitle": {{
    "text": "副标题",
    "size": 20,
    "color": "#00d4ff"
  }},
  "elements": [
    {{
      "type": "mega_number|progress_bar|ring_chart|bar_chart|gauge|card|icon_stat",
      "value": "数据值",
      "unit": "单位",
      "label": "标签",
      "color": "#00d4ff",
      "size": "large|medium|small"
    }}
  ],
  "tags": ["标签1", "标签2"]
}}```

输出纯JSON数组。每个场景的设计必须不同！"""


def _check_design_quality(designs: list) -> list[str]:
    """Check design quality and return list of issues (empty = good)."""
    issues = []
    from collections import Counter

    # Check 1: Too many same layout
    layouts = [d.get("layout", {}).get("type", "") for d in designs]
    layout_counts = Counter(layouts)
    for layout, count in layout_counts.items():
        if count > 2:
            issues.append(f"too many {layout}: {count}")

    # Check 2: Too few elements per scene
    for i, d in enumerate(designs):
        el_count = len(d.get("elements", []))
        if el_count < 4:
            issues.append(f"F{i+1} only {el_count} elements (need 4+)")

    # Check 3: Same background type
    bg_types = [d.get("bg", {}).get("type", "") for d in designs]
    if len(set(bg_types)) < len(bg_types) * 0.5:
        issues.append(f"low bg diversity: {len(set(bg_types))}/{len(bg_types)}")

    # Check 4: Too many mega_number
    all_types = []
    for d in designs:
        all_types.extend(el.get("type", "") for el in d.get("elements", []))
    mega_count = sum(1 for t in all_types if t == "mega_number")
    if mega_count > len(designs) * 0.5:
        issues.append(f"too many mega_number: {mega_count}/{len(all_types)}")

    return issues


def generate_creative_designs(topic: str, storyboard: list[dict]) -> list[dict]:
    """Let LLM design each scene creatively within constraints."""
    scene_data = json.dumps([
        {
            "scene_id": s.get("scene_id", i+1),
            "title": s.get("title", ""),
            "subtitle": s.get("subtitle", ""),
            "narration": s.get("narration", "")[:100],
            "key_data": s.get("key_data", []),
            "key_points": s.get("key_points", []),
            "visual_type": s.get("visual_type", "data"),
        }
        for i, s in enumerate(storyboard)
    ], ensure_ascii=False, indent=2)

    prompt = DESIGN_PROMPT_TEMPLATE.format(
        count=len(storyboard),
        topic=topic,
        scene_data=scene_data
    )

    for attempt in range(3):
        resp = call_llm(prompt, max_tokens=8000)
        designs = extract_json(resp)

        if isinstance(designs, list) and len(designs) == len(storyboard):
            issues = _check_design_quality(designs)
            if not issues:
                print(f"  ✅ Design quality check PASSED (attempt {attempt+1})")
                return designs
            else:
                print(f"  ⚠️ Design quality issues (attempt {attempt+1}): {issues}")
                if attempt < 2:
                    continue

        if isinstance(designs, list) and len(designs) == len(storyboard):
            return designs

    print(f"  ⚠️ LLM design failed after 3 attempts, generating fallback")
    return _fallback_designs(topic, storyboard)


def _fallback_designs(topic: str, storyboard: list[dict]) -> list[dict]:
    """Generate diverse fallback designs when LLM fails."""
    palettes = [
        {"primary": "#00d4ff", "secondary": "#ff6b35"},
        {"primary": "#3b82f6", "secondary": "#ef4444"},
        {"primary": "#06b6d4", "secondary": "#f59e0b"},
        {"primary": "#8b5cf6", "secondary": "#10b981"},
        {"primary": "#ec4899", "secondary": "#6366f1"},
        {"primary": "#14b8a6", "secondary": "#f97316"},
    ]

    layouts = [
        {"type": "diagonal"},
        {"type": "asymmetric"},
        {"type": "split_h"},
        {"type": "dashboard"},
        {"type": "timeline"},
        {"type": "full_bleed"},
    ]

    bg_types = ["particle_tech", "minimal_gradient", "geometric_lines", "subtle_glow"]

    designs = []
    for i, s in enumerate(storyboard):
        p = palettes[i % len(palettes)]
        kd_list = s.get("key_data", [])
        if not kd_list:
            kd_list = [{"value": "—", "unit": "", "label": ""}]

        elements = []
        # First element: mega_number (main data)
        kd0 = kd_list[0] if kd_list else {"value": "—", "unit": "", "label": ""}
        elements.append({
            "type": "mega_number",
            "value": kd0.get("value", ""),
            "unit": kd0.get("unit", ""),
            "label": kd0.get("label", ""),
            "color": p["primary"],
            "size": "large"
        })
        # Second element: progress_bar or ring_chart
        if len(kd_list) > 1:
            kd1 = kd_list[1]
            elements.append({
                "type": "progress_bar",
                "value": kd1.get("value", ""),
                "unit": kd1.get("unit", ""),
                "label": kd1.get("label", ""),
                "color": p["secondary"],
                "size": "medium"
            })
        else:
            elements.append({
                "type": "ring_chart",
                "value": "75",
                "unit": "%",
                "label": "完成度",
                "color": p["secondary"],
                "size": "medium"
            })
        # Third element: card (for key points)
        key_points = s.get("key_points", [])
        if key_points:
            elements.append({
                "type": "card",
                "value": key_points[0][:30],
                "unit": "",
                "label": "要点",
                "color": "#ffffff",
                "size": "medium"
            })
        else:
            elements.append({
                "type": "gauge",
                "value": kd_list[2].get("value", "50") if len(kd_list) > 2 else "50",
                "unit": kd_list[2].get("unit", "") if len(kd_list) > 2 else "",
                "label": kd_list[2].get("label", "指标") if len(kd_list) > 2 else "指标",
                "color": p["primary"],
                "size": "medium"
            })
        # Fourth element: card or icon_stat
        if len(kd_list) > 3:
            elements.append({
                "type": "card",
                "value": kd_list[3].get("value", "—"),
                "unit": kd_list[3].get("unit", ""),
                "label": kd_list[3].get("label", "数据"),
                "color": p["secondary"],
                "size": "small"
            })
        else:
            elements.append({
                "type": "icon_stat",
                "value": "—",
                "unit": "",
                "label": "数据",
                "color": p["secondary"],
                "size": "small"
            })

        design = {
            "bg": {"type": bg_types[i % len(bg_types)], "color": "#0a0a1a"},
            "layout": layouts[i % len(layouts)],
            "title": {"text": s.get("title", topic)[:15], "size": 48, "color": "#ffffff", "weight": 900},
            "subtitle": {"text": s.get("subtitle", ""), "size": 20, "color": p["primary"]},
            "elements": elements,
            "tags": s.get("tags", []),
        }
        designs.append(design)

    return designs


# ============================================================
# CSS Animation Library — 统一入场动画 + 呼吸感
# ============================================================

CSS_ANIMATIONS = '''<style>
  /* === 入场动画 === */
  @keyframes fadeInUp {
    from { opacity:0; transform:translateY(30px); }
    to { opacity:1; transform:translateY(0); }
  }
  @keyframes fadeInDown {
    from { opacity:0; transform:translateY(-30px); }
    to { opacity:1; transform:translateY(0); }
  }
  @keyframes fadeInLeft {
    from { opacity:0; transform:translateX(-40px); }
    to { opacity:1; transform:translateX(0); }
  }
  @keyframes fadeInRight {
    from { opacity:0; transform:translateX(40px); }
    to { opacity:1; transform:translateX(0); }
  }
  @keyframes scaleIn {
    from { opacity:0; transform:scale(0.8); }
    to { opacity:1; transform:scale(1); }
  }

  /* === 呼吸/脉冲动画 === */
  @keyframes breathe {
    0%,100% { transform:scale(1); opacity:0.9; }
    50% { transform:scale(1.02); opacity:1; }
  }
  @keyframes glowPulse {
    0%,100% { filter:drop-shadow(0 0 8px var(--glow-color)); }
    50% { filter:drop-shadow(0 0 20px var(--glow-color)); }
  }
  @keyframes softFloat {
    0%,100% { transform:translateY(0); }
    50% { transform:translateY(-4px); }
  }

  /* === 流光效果 === */
  @keyframes lightFlow {
    0% { transform:translateX(-100%); }
    100% { transform:translateX(100%); }
  }
  @keyframes lightFlowVertical {
    0% { transform:translateY(-100%); }
    100% { transform:translateY(100%); }
  }

  /* === 进度条生长 === */
  @keyframes barGrow {
    from { width:0%; }
  }

  /* === 应用类 === */
  .anim-fade-up { animation: fadeInUp 0.6s ease-out both; }
  .anim-fade-down { animation: fadeInDown 0.6s ease-out both; }
  .anim-fade-left { animation: fadeInLeft 0.5s ease-out both; }
  .anim-fade-right { animation: fadeInRight 0.5s ease-out both; }
  .anim-scale { animation: scaleIn 0.6s cubic-bezier(0.34,1.56,0.64,1) both; }
  .anim-breathe { animation: breathe 3s ease-in-out infinite; }
  .anim-glow { animation: glowPulse 2.5s ease-in-out infinite; }
  .anim-float { animation: softFloat 4s ease-in-out infinite; }
  .anim-bar-grow { animation: barGrow 1s ease-out both; }
  .anim-light-flow {
    animation: lightFlow 3s linear infinite;
  }
  .anim-light-flow-v {
    animation: lightFlowVertical 4s linear infinite;
  }

  /* === 延迟类 === */
  .d1 { animation-delay: 0.1s; }
  .d2 { animation-delay: 0.2s; }
  .d3 { animation-delay: 0.3s; }
  .d4 { animation-delay: 0.4s; }
  .d5 { animation-delay: 0.5s; }
  .d6 { animation-delay: 0.6s; }
</style>'''


# ============================================================
# Background Renderers — 4种高质量背景模板
# ============================================================

def _render_bg(spec: dict) -> str:
    """Render background from design spec with light flow effect."""
    bg_type = spec.get("type", "minimal_gradient")
    color = spec.get("color", "#0a0a1a")

    # 流光效果 — 水平流光（更明显）
    light_flow = f'''<div style="position:absolute;top:0;left:0;width:100%;height:100%;overflow:hidden;pointer-events:none;">
      <div class="anim-light-flow" style="position:absolute;top:25%;left:0;width:60%;height:2px;
        background:linear-gradient(90deg,transparent,rgba(0,212,255,0.25),transparent);
        filter:blur(2px);"></div>
      <div class="anim-light-flow" style="position:absolute;top:55%;left:0;width:50%;height:2px;
        background:linear-gradient(90deg,transparent,rgba(59,130,246,0.2),transparent);
        filter:blur(2px);animation-delay:1.5s;"></div>
      <div class="anim-light-flow" style="position:absolute;top:80%;left:0;width:40%;height:1px;
        background:linear-gradient(90deg,transparent,rgba(0,212,255,0.15),transparent);
        filter:blur(1px);animation-delay:0.8s;"></div>
    </div>'''

    if bg_type == "particle_tech":
        return f'''<div style="position:absolute;top:0;left:0;width:100%;height:100%;background:{color};"></div>
    <div style="position:absolute;top:0;left:0;width:100%;height:100%;opacity:0.18;
      background-image:radial-gradient(circle,#00d4ff 1.5px,transparent 1.5px);
      background-size:25px 25px;"></div>
    <div style="position:absolute;top:15%;left:8%;width:350px;height:350px;border-radius:50%;
      background:radial-gradient(circle,rgba(0,212,255,0.08) 0%,transparent 70%);filter:blur(70px);"></div>
    <div style="position:absolute;bottom:15%;right:8%;width:300px;height:300px;border-radius:50%;
      background:radial-gradient(circle,rgba(59,130,246,0.08) 0%,transparent 70%);filter:blur(60px);"></div>
    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:200px;height:200px;border-radius:50%;
      border:1px solid rgba(0,212,255,0.06);"></div>
    {light_flow}'''

    elif bg_type == "geometric_lines":
        return f'''<div style="position:absolute;top:0;left:0;width:100%;height:100%;background:{color};"></div>
    <div style="position:absolute;top:0;left:0;width:100%;height:100%;opacity:0.08;
      background-image:linear-gradient(rgba(255,255,255,0.12) 1px,transparent 1px),
      linear-gradient(90deg,rgba(255,255,255,0.12) 1px,transparent 1px);
      background-size:50px 50px;"></div>
    <div style="position:absolute;top:25%;left:15%;width:250px;height:250px;
      border:1px solid rgba(0,212,255,0.1);border-radius:50%;"></div>
    <div style="position:absolute;bottom:20%;right:10%;width:180px;height:180px;
      border:1px solid rgba(59,130,246,0.1);border-radius:50%;"></div>
    <div style="position:absolute;top:60%;left:60%;width:120px;height:120px;
      border:1px solid rgba(0,212,255,0.06);border-radius:50%;"></div>
    {light_flow}'''

    elif bg_type == "subtle_glow":
        return f'''<div style="position:absolute;top:0;left:0;width:100%;height:100%;background:{color};"></div>
    <div style="position:absolute;top:30%;left:30%;width:400px;height:400px;border-radius:50%;
      background:radial-gradient(circle,rgba(0,212,255,0.05) 0%,transparent 70%);filter:blur(80px);"></div>
    <div style="position:absolute;bottom:20%;right:20%;width:300px;height:300px;border-radius:50%;
      background:radial-gradient(circle,rgba(59,130,246,0.05) 0%,transparent 70%);filter:blur(60px);"></div>
    {light_flow}'''

    else:  # minimal_gradient
        return f'''<div style="position:absolute;top:0;left:0;width:100%;height:100%;
      background:linear-gradient(135deg,{color} 0%,#111827 100%);"></div>
    <div style="position:absolute;top:0;right:0;width:50%;height:50%;
      background:radial-gradient(circle,rgba(0,212,255,0.03) 0%,transparent 70%);filter:blur(60px);"></div>
    {light_flow}'''


# ============================================================
# Element Renderers — 统一风格的数据可视化+卡片
# ============================================================

def _safe_num(val) -> float:
    """Safely convert to number."""
    try:
        return float(re.sub(r'[^\d.\-]', '', str(val)))
    except:
        return 50.0


def _render_element(el: dict, index: int, total: int, layout_spec: dict, duration: float) -> str:
    """Render a data visualization element or card."""
    el_type = el.get("type", "card")
    value = el.get("value", "")
    unit = el.get("unit", "")
    label = el.get("label", "")
    color = el.get("color", "#00d4ff")
    if isinstance(color, list):
        color = color[0] if color else "#00d4ff"
    size = el.get("size", "medium")

    delay = 0.3 + index * 0.15
    track = 3 + index
    glow_color = str(color) + "60"  # 更强的glow

    # Layout-aware positioning
    layout_type = layout_spec.get("type", "diagonal")

    # Position calculation — fill the entire frame (20% to 90%)
    if layout_type == "diagonal":
        diag_positions = [
            (8, 22), (55, 28), (10, 50), (60, 55), (15, 72), (65, 78)
        ]
        if index < len(diag_positions):
            x_pct, y_pct = diag_positions[index]
        else:
            x_pct = 8 + index * 10
            y_pct = 22 + index * 10
    elif layout_type == "asymmetric":
        # 60/40 split — 左侧为主，右侧为辅
        if index == 0:
            x_pct = 5
            y_pct = 25  # 主数据
        elif index == 1:
            x_pct = 55
            y_pct = 25  # 次数据
        elif index == 2:
            x_pct = 5
            y_pct = 55  # 卡片1
        elif index == 3:
            x_pct = 55
            y_pct = 55  # 卡片2
        else:
            x_pct = 30
            y_pct = 75  # 补充
    elif layout_type == "split_h":
        if index < total // 2:
            x_pct = 4 + (index * 6) % 12
            y_pct = 22 + index * 20
        else:
            x_pct = 52 + ((index - total // 2) * 6) % 12
            y_pct = 22 + (index - total // 2) * 20
    elif layout_type == "dashboard":
        col = index % 2
        row = index // 2
        x_pct = 4 + col * 48
        y_pct = 22 + row * 25
    elif layout_type == "timeline":
        # 水平时间轴 — 元素沿水平线分布，交替上下
        x_pct = 5 + index * (85 // max(total, 1))
        y_pct = 35 + (index % 2) * 25  # 交替上下
    else:  # full_bleed
        fb_positions = [
            (3, 20), (50, 20), (3, 50), (50, 50), (25, 35), (25, 65)
        ]
        if index < len(fb_positions):
            x_pct, y_pct = fb_positions[index]
        else:
            x_pct = 3 + (index * 15) % 60
            y_pct = 20 + (index * 12) % 50

    # Render based on element type
    if el_type == "mega_number":
        font_size = {"large": 120, "medium": 80, "small": 60}.get(size, 120)
        return f'''
    <div class="clip anim-scale" data-start="{delay}" data-duration="{duration-delay}" data-track-index="{track}"
         style="position:absolute;top:{y_pct}%;left:{x_pct}%;z-index:10;">
      <div style="font-size:12px;color:{color}88;letter-spacing:2px;text-transform:uppercase;">{label}</div>
      <div style="font-size:{font_size}px;font-weight:900;line-height:0.9;margin-top:6px;
        background:linear-gradient(180deg,#fff 10%,{color} 100%);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
        filter:drop-shadow(0 0 30px {glow_color});">{value}</div>
      <div style="font-size:20px;color:{color};font-weight:700;letter-spacing:4px;">{unit}</div>
    </div>'''

    elif el_type == "progress_bar":
        val = _safe_num(value)
        pct = min(100, max(10, val))
        return f'''
    <div class="clip anim-fade-up" data-start="{delay}" data-duration="{duration-delay}" data-track-index="{track}"
         style="position:absolute;top:{y_pct}%;left:{x_pct}%;width:40%;z-index:10;">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
        <span style="font-size:14px;color:rgba(255,255,255,0.7);">{label}</span>
        <span style="font-size:18px;color:{color};font-weight:900;">{value}{unit}</span>
      </div>
      <div style="height:8px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden;">
        <div class="anim-bar-grow" style="height:100%;width:{pct}%;background:linear-gradient(90deg,{color},{color}80);
          border-radius:4px;box-shadow:0 0 8px {glow_color};animation-delay:{delay}s;"></div>
      </div>
    </div>'''

    elif el_type == "ring_chart":
        val = _safe_num(value)
        pct = min(100, max(5, val))
        r = 40
        circ = 2 * 3.14159 * r
        dash = circ * pct / 100
        return f'''
    <div class="clip anim-scale" data-start="{delay}" data-duration="{duration-delay}" data-track-index="{track}"
         style="position:absolute;top:{y_pct}%;left:{x_pct}%;text-align:center;z-index:10;">
      <svg width="100" height="100" viewBox="0 0 100 100" style="margin:0 auto;display:block;">
        <circle cx="50" cy="50" r="{r}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="6"/>
        <circle cx="50" cy="50" r="{r}" fill="none" stroke="{color}" stroke-width="6"
          stroke-dasharray="{dash} {circ}" stroke-linecap="round"
          transform="rotate(-90 50 50)" style="filter:drop-shadow(0 0 6px {glow_color});"/>
      </svg>
      <div style="font-size:28px;font-weight:900;color:{color};margin-top:-70px;position:relative;
        text-shadow:0 0 10px {glow_color};">{value}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.5);margin-top:40px;">{unit}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:2px;">{label}</div>
    </div>'''

    elif el_type == "bar_chart":
        val = _safe_num(value)
        pct = min(100, max(10, val))
        bar_h = 40 + int(pct * 0.6)
        return f'''
    <div class="clip anim-fade-up" data-start="{delay}" data-duration="{duration-delay}" data-track-index="{track}"
         style="position:absolute;top:{y_pct}%;left:{x_pct}%;width:15%;text-align:center;z-index:10;">
      <div style="font-size:18px;color:{color};font-weight:900;text-shadow:0 0 8px {glow_color};">{value}{unit}</div>
      <div style="width:80%;height:{bar_h}px;background:linear-gradient(180deg,{color},{color}40);
        border-radius:6px 6px 0 0;margin:6px auto 0;box-shadow:0 0 10px {glow_color};
        animation:barGrow 1s ease-out both;animation-delay:{delay}s;"></div>
      <div style="font-size:12px;color:rgba(255,255,255,0.6);margin-top:4px;">{label}</div>
    </div>'''

    elif el_type == "gauge":
        val = _safe_num(value)
        pct = min(100, max(5, val))
        r = 50
        circ = 3.14159 * r
        dash = circ * pct / 100
        needle_angle = -90 + (pct / 100) * 180
        return f'''
    <div class="clip anim-scale" data-start="{delay}" data-duration="{duration-delay}" data-track-index="{track}"
         style="position:absolute;top:{y_pct}%;left:{x_pct}%;width:160px;text-align:center;z-index:10;">
      <svg width="160" height="100" viewBox="0 0 160 100" style="display:block;margin:0 auto;">
        <path d="M 10 90 A 70 70 0 0 1 150 90" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="12" stroke-linecap="round"/>
        <path d="M 10 90 A 70 70 0 0 1 150 90" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round"
          stroke-dasharray="{dash} {circ}" style="filter:drop-shadow(0 0 8px {glow_color});"/>
        <line x1="80" y1="90" x2="80" y2="35" stroke="{color}" stroke-width="2"
          transform="rotate({needle_angle} 80 90)" style="filter:drop-shadow(0 0 4px {glow_color});"/>
        <circle cx="80" cy="90" r="5" fill="{color}" style="filter:drop-shadow(0 0 5px {glow_color});"/>
      </svg>
      <div style="font-size:36px;font-weight:900;color:{color};margin-top:-55px;position:relative;
        text-shadow:0 0 15px {glow_color};">{value}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.5);margin-top:25px;">{unit}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:2px;">{label}</div>
    </div>'''

    elif el_type == "card":
        # 卡片 — 用于展示文字信息、要点、标签等
        # 最小宽度25%，字体≥16px，确保可读性
        card_width = max(25, 30)  # 最小25%
        font_size = max(16, 16)  # 最小16px
        return f'''
    <div class="clip anim-fade-up" data-start="{delay}" data-duration="{duration-delay}" data-track-index="{track}"
         style="position:absolute;top:{y_pct}%;left:{x_pct}%;width:{card_width}%;z-index:10;
         border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:20px;
         background:rgba(255,255,255,0.05);backdrop-filter:blur(10px);">
      <div style="font-size:12px;color:{color}88;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">{label}</div>
      <div style="font-size:{font_size}px;color:#ffffff;line-height:1.5;">{value}</div>
    </div>'''

    elif el_type == "icon_stat":
        return f'''
    <div class="clip anim-scale" data-start="{delay}" data-duration="{duration-delay}" data-track-index="{track}"
         style="position:absolute;top:{y_pct}%;left:{x_pct}%;z-index:10;display:flex;align-items:center;gap:12px;">
      <div style="width:40px;height:40px;border-radius:10px;background:{color}15;
        display:flex;align-items:center;justify-content:center;border:1px solid {color}30;">
        <div style="font-size:18px;">{label[:1]}</div>
      </div>
      <div>
        <div style="font-size:32px;font-weight:900;color:{color};line-height:1;">{value}{unit}</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.5);">{label}</div>
      </div>
    </div>'''

    else:
        # Default: card
        return f'''
    <div class="clip anim-fade-up" data-start="{delay}" data-duration="{duration-delay}" data-track-index="{track}"
         style="position:absolute;top:{y_pct}%;left:{x_pct}%;width:30%;z-index:10;
         border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:16px;
         background:rgba(255,255,255,0.05);">
      <div style="font-size:12px;color:{color}88;letter-spacing:2px;">{label}</div>
      <div style="font-size:24px;font-weight:900;color:{color};margin-top:6px;">{value}{unit}</div>
    </div>'''


def _render_tags(tags: list, primary: str, duration: float) -> str:
    """移除底部标签 — 无用信息污染画面"""
    return ""


def _render_title(spec: dict, layout_spec: dict, duration: float) -> str:
    """Render title element."""
    title = spec.get("text", "")
    if not title:
        return ""
    size = spec.get("size", 48)
    color = spec.get("color", "#ffffff")
    weight = spec.get("weight", 900)

    layout_type = layout_spec.get("type", "diagonal")
    if layout_type in ("diagonal", "asymmetric"):
        style = "top:5%;left:5%;"
    elif layout_type == "split_h":
        style = "top:5%;left:50%;transform:translateX(-50%);text-align:center;"
    elif layout_type == "full_bleed":
        style = "top:5%;left:50%;transform:translateX(-50%);text-align:center;"
    else:
        style = "top:5%;left:5%;"

    return f'''
    <div class="clip anim-fade-up" data-start="0.1" data-duration="{duration-0.1}" data-track-index="1"
         style="position:absolute;{style}z-index:10;">
      <div style="font-size:{size}px;font-weight:{weight};color:{color};letter-spacing:2px;line-height:1.2;">{title}</div>
      <div style="width:60px;height:2px;background:linear-gradient(90deg,{color}60,transparent);margin-top:8px;border-radius:1px;"></div>
    </div>'''


def _render_subtitle(spec: dict, layout_spec: dict, duration: float) -> str:
    """Render subtitle element."""
    text = spec.get("text", "")
    if not text:
        return ""
    size = spec.get("size", 18)
    color = spec.get("color", "#00d4ff")

    layout_type = layout_spec.get("type", "diagonal")
    if layout_type in ("diagonal", "asymmetric"):
        style = "top:12%;left:5%;"
    elif layout_type in ("split_h", "full_bleed"):
        style = "top:12%;left:50%;transform:translateX(-50%);text-align:center;"
    else:
        style = "top:12%;left:5%;"

    return f'''
    <div class="clip anim-fade-up d1" data-start="0.2" data-duration="{duration-0.2}" data-track-index="2"
         style="position:absolute;{style}z-index:10;">
      <div style="font-size:{size}px;color:{color};">{text}</div>
    </div>'''


# ============================================================
# Scene Renderer
# ============================================================

def render_scene(scene_id: int, design: dict, storyboard_item: dict, duration: float) -> str:
    """Render a complete scene from design spec."""
    bg = design.get("bg", {})
    layout = design.get("layout", {})
    title_spec = design.get("title", {})
    subtitle_spec = design.get("subtitle", {})
    elements = design.get("elements", [])
    tags = design.get("tags", [])

    primary = elements[0].get("color", "#00d4ff") if elements else "#00d4ff"

    bg_html = _render_bg(bg)
    title_html = _render_title(title_spec, layout, duration)
    subtitle_html = _render_subtitle(subtitle_spec, layout, duration)

    elements_html = ""
    for i, el in enumerate(elements[:6]):
        elements_html += _render_element(el, i, len(elements), layout, duration)

    tags_html = _render_tags(tags, primary, duration)

    composition_id = f"beat-{scene_id}"
    return f'''<template id="{composition_id}-template">
  <div data-composition-id="{composition_id}" data-width="1920" data-height="1080">
    {bg_html}
    {CSS_ANIMATIONS}
    {title_html}
    {subtitle_html}
    {elements_html}
    {tags_html}
    <style>[data-composition-id="{composition_id}"] {{ font-family:"Inter","Noto Sans SC",sans-serif; }}</style>
    <script>
      (function() {{
        if (!window.__timelines) window.__timelines = {{}};
        var tl = gsap.timeline({{paused:true}});
        window.__timelines["{composition_id}"] = tl;
      }})();
    </script>
  </div>
</template>'''


# ============================================================
# Step 5: Generate index.html + Render
# ============================================================

def generate_index_html(storyboard: list[dict], output_dir: Path) -> Path:
    """Generate index.html with all compositions."""
    total_dur = sum(s.get("duration", 5.0) for s in storyboard)
    cur_t = 0.0
    beats = ""
    for s in storyboard:
        sid = s["scene_id"]
        dur = s.get("duration", 5.0)
        beats += f'<div id="beat-{sid}" class="clip" data-composition-id="beat-{sid}" data-composition-src="compositions/beat-{sid}.html" data-start="{cur_t}" data-duration="{dur}" data-track-index="0" data-width="1920" data-height="1080"></div>'
        cur_t += dur

    idx_html = f'''<!doctype html><html lang="zh"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1920,height=1080"/>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>*{{margin:0;padding:0;box-sizing:border-box;}}html,body{{margin:0;width:1920px;height:1080px;overflow:hidden;background:#050508;}}</style>
</head><body><div id="root" data-composition-id="main" data-start="0" data-duration="{total_dur}" data-width="1920" data-height="1080">{beats}</div>
<script>window.__timelines={{}};const tl=gsap.timeline({{paused:true}});tl.pause();window.__timelines["main"]=tl;</script></body></html>'''

    idx_path = output_dir / "index.html"
    idx_path.write_text(idx_html, encoding="utf-8")
    return idx_path


def render_video(output_dir: Path) -> Optional[Path]:
    """Render with HyperFrames."""
    import subprocess
    out = output_dir / "rendered.mp4"
    print(f"  🎬 Rendering with HyperFrames...")
    try:
        r = subprocess.run(
            f'hyperframes render "{output_dir}" -o "{out}" --fps 30 --quality draft',
            shell=True, capture_output=True, text=True, timeout=300
        )
        if r.returncode == 0:
            print(f"  ✅ Rendered: {out} ({out.stat().st_size / 1024:.0f} KB)")
            return out
        else:
            print(f"  ❌ Render failed: {r.stderr[:300]}")
            return None
    except Exception as e:
        print(f"  ❌ Render error: {e}")
        return None


def extract_frames(video_path: Path, storyboard: list[dict]) -> list[Path]:
    """Extract middle frame from each scene."""
    import subprocess
    frames = []
    cur_t = 0.0
    for i, s in enumerate(storyboard):
        dur = s.get("duration", 5.0)
        t = cur_t + dur / 2
        fp = video_path.parent / f"frame_{i+1:02d}.jpg"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(t), "-i", str(video_path), "-frames:v", "1", "-q:v", "2", str(fp)],
                capture_output=True, timeout=30
            )
            frames.append(fp)
        except:
            pass
        cur_t += dur
    print(f"  ✅ Extracted {len(frames)} frames")
    return frames


# ============================================================
# Full Pipeline
# ============================================================

def run_full_pipeline(topic: str, output_dir: Path) -> dict:
    """Run complete pipeline: script → storyboard → design → render → extract frames."""
    output_dir.mkdir(parents=True, exist_ok=True)
    comp_dir = output_dir / "compositions"
    comp_dir.mkdir(parents=True, exist_ok=True)

    result = {"topic": topic, "output_dir": str(output_dir), "scenes": []}

    print(f"\n{'='*60}")
    print(f"🎬 V18 Pipeline — {topic}")
    print(f"{'='*60}")
    print(f"[Step 1/5] Generating script...")
    script = generate_script(topic)
    print(f"  ✅ {len(script)} scenes")

    print(f"[Step 2/5] Extracting storyboard data...")
    storyboard = extract_storyboard(topic, script)
    print(f"  ✅ {len(storyboard)} scene data extracted")

    merged = []
    for i, s in enumerate(script):
        sb = storyboard[i] if i < len(storyboard) else {}
        merged.append({
            "scene_id": s.get("scene_id", i + 1),
            "narration": s.get("narration", ""),
            "duration": s.get("duration", 5.0),
            "visual_type": s.get("visual_type", "data"),
            "title": sb.get("title", s.get("narration", "")[:15]),
            "subtitle": sb.get("subtitle", ""),
            "key_data": sb.get("key_data", []),
            "key_points": sb.get("key_points", []),
            "tags": sb.get("tags", []),
            "quote_text": sb.get("quote_text", ""),
        })

    (output_dir / "storyboard.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[Step 3/5] LLM generating creative designs...")
    designs = generate_creative_designs(topic, merged)

    (output_dir / "design_specs.json").write_text(
        json.dumps(designs, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    layout_types = [d.get("layout", {}).get("type", "?") for d in designs]
    bg_types = [d.get("bg", {}).get("type", "?") for d in designs]
    print(f"  📊 Layout types: {layout_types}")
    print(f"  📊 BG types: {bg_types}")

    print(f"[Step 4/5] Rendering compositions...")
    for i, (scene, design) in enumerate(zip(merged, designs)):
        sid = scene["scene_id"]
        dur = scene["duration"]
        html = render_scene(sid, design, scene, dur)
        (comp_dir / f"beat-{sid}.html").write_text(html, encoding="utf-8")
        print(f"  beat-{sid}.html ({len(html)} chars)")

    print(f"[Step 5/5] Generating index.html and rendering video...")
    generate_index_html(merged, output_dir)
    video_path = render_video(output_dir)

    if video_path:
        frames = extract_frames(video_path, merged)
        result["video"] = str(video_path)
        result["frames"] = [str(f) for f in frames]
        result["video_size_kb"] = video_path.stat().st_size / 1024

    result["storyboard"] = merged
    result["designs"] = designs
    result["layout_types"] = layout_types
    result["bg_types"] = bg_types

    (output_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    return result
