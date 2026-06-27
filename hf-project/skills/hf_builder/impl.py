#!/usr/bin/env python3
"""
hf_builder v5 — HyperFrames 原生方式 + 视觉丰富度保证

核心理念（来自 HyperFrames best practices）：
- HTML 是视频的源码，每个场景是一个完整的 HTML composition
- Layout Before Animation：先写静态终态，再加 gsap.from() 入场动画
- storyboard 的 depth_layers 决定每个场景的视觉元素
- design.md 决定配色/字体/风格
- 不用模板，LLM 根据上游数据原创构建每个场景
"""
import os
import sys
import json
import re
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(__file__))

# ============================================================
# LLM
# ============================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from llm_utils import call_llm as _shared_call_llm

def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 12000) -> str:
    return _shared_call_llm(prompt, system_prompt, max_tokens, timeout=300, task="creative")


# ============================================================
# 加载上游数据
# ============================================================

def load_design_system(project_root: Path) -> str:
    p = project_root / "output" / "design.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""

def load_design_specs(project_root: Path) -> dict:
    p = project_root / "output" / "design_specs.json"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        specs = json.load(f)
    return {s.get("scene_id", i+1): s for i, s in enumerate(specs)}


# ============================================================
# 场景 HTML 生成 — LLM 原创构建
# ============================================================

# 模块级分辨率配置（由run()设置，auto_fix/fallback读取）
_VIDEO_W = 1920
_VIDEO_H = 1080

SCENE_PROMPT = """你是 HyperFrames 视频合成专家。为以下场景编写完整 HTML。

## 设计系统配色
{design_md}

## 场景
- ID: {scene_id} | 类型: {visual_type} | 时长: {duration}s
- 概念: {concept}
- 口播参考（仅供理解场景语义，**严禁**将口播原文放入画面。可提取3-5个关键词作为标签，或取前15字作主标题。画面中不得出现超过15字的连续口播原文）: {narration}
- 关键数据: {key_elements}
- 可视化层次: {depth_layers}
- 元素密度: 至少 {density_target} 个 | 动画: {animations}

## ⚠️ 图表（MUST：chart_type 不为 null 时必须画图表！）
- 当前场景 chart_type = {chart_type}
- **如果 chart_type 不是 null，你必须在 HTML 中画出对应的图表，否则场景不合格！**
- bar_chart: 5-7根CSS div柱子，GSAP scaleY:0→1生长，渐变颜色
- line_chart: SVG polyline + stroke-dasharray 动画绘制
- pie_chart: SVG circle + stroke-dasharray 扇形，最多6片
- kpi_grid: 3-4个卡片并排，每个含标签+数值+趋势箭头

## ⚠️ 镜头运动（MUST：camera_motion 不为 null 时必须实现！）
- 当前场景 camera_motion = {camera_motion}
- **如果 camera_motion 不是 null，你必须在 GSAP 中实现对应的镜头运动！**
- dolly_in: tl.from(".scene", {{scale:1.15, duration:1.2, ease:"power2.out"}}, 0)
- dolly_out: tl.from(".scene", {{scale:0.9, duration:1.0, ease:"power2.out"}}, 0)
- pan_left: tl.from(".scene", {{x:-60, duration:0.8, ease:"power3.out"}}, 0)
- pan_right: tl.from(".scene", {{x:60, duration:0.8, ease:"power3.out"}}, 0)
- zoom_in: tl.from("#main-content", {{scale:0.8, duration:0.6, ease:"back.out(1.4)"}}, 0)

## 硬性规则（违反=渲染失败）
1. 输出完整 <!DOCTYPE html>，html标签: data-composition-id="{composition_id}" data-width="1920" data-height="1080"
2. 引入 GSAP CDN，创建 gsap.timeline({{paused:true}}) 注册到 window.__timelines["{composition_id}"]
3. 所有内容在 class="scene" div 中
4. **⚠️ 绝对禁止在CSS/inline style中设置opacity:0！** 这会导致渲染器看不到内容。所有元素CSS中必须opacity:1（或不写opacity）。入场动画用GSAP的tl.from({{opacity:0}})即可，不要在HTML标签的style属性里写opacity:0。
5. 不要出场动画，不要 repeat:-1（呼吸动画除外），不要 Math.random()
6. 卡片呼吸感: scale 1.0→1.02→1.0, duration 2.5s, repeat:-1, yoyo:true
7. **所有样式必须用内联 style="" 属性**（HF沙箱不支持 <style> 块）
8. 不要 CSS class 定义，不要 <style> 块
9. **每个HTML标签最多一个style属性**，禁止重复style=""（如 `<div style="a" style="b">` 是错的，应写 `<div style="a; b">`）
10. 背景必须深色 #1a1a2e，禁止白色/浅色
11. 不要用 Google Fonts
12. CSS 注释中不能有中文字符

## 排版规范（V5 强制执行，违反=低级感）
### 字号标准（1080p）
- 主标题: 80-120px, font-weight:900, 主色+发光(text-shadow 0 0 30px)
- 核心数据: 100-140px, JetBrains Mono, font-weight:900, 金色/强调色
- 副标题: 36-48px, font-weight:600
- 正文/标签: 20-28px, font-weight:400
- 辅助文字: 16-20px, 灰色#888-#999
- Ghost text水印: 200-300px, 白色3-5%透明度
### 字体
- 正文: 'Inter','Noto Sans SC',sans-serif | 数据: 'JetBrains Mono',monospace
- 行高:1.5-1.6 | letter-spacing:0.02em
- 每个场景最多2种字体（正文1种+数据1种）
### 安全区
- 所有文字必须在画面80%范围内（上下左右各192px边距）
- 禁止元素贴边
### 对比度
- 白字深底（21:1）优先，禁止浅色文字在浅色背景上
- 核心数据必须高亮色（金色#FFD700/青色#00D4FF/紫色#A855F7），不能用灰色
### 缓动曲线（禁止linear）
- 入场: easeOutCubic 或 power3.out
- 弹性: back.out(1.7)
- 呼吸: sine.inOut
- 禁止: linear, none

## GSAP动画正确写法（严格遵守）
```javascript
// ✅ 正确：CSS中不写opacity，用GSAP控制
tl.from("#el", {{opacity: 0, y: 50, duration: 0.8, ease: "power3.out"}});
// ❌ 错误：在CSS中写opacity:0
// <div style="opacity: 0;">  ← 绝对禁止！
```
**记住：CSS中的opacity只写1或不写。GSAP的from()会自动处理从0到1的动画。**

## 数字冲击效果代码示例（每个场景必须有！）
```javascript
tl.from("#main-number", {{
    opacity: 0, scale: 2.5, duration: 0.6, ease: "back.out(1.7)"
}}, 0.5);
gsap.to("#main-number", {{
    textShadow: "0 0 40px rgba(255,215,0,0.8)", duration: 1.5, repeat: -1, yoyo: true, ease: "sine.inOut"
}});
```

## 场景转场（第一个场景不需要入场转场，最后一个不需要出场转场）
- 入场转场: tl.from(".scene", {{opacity:0, duration:0.4, ease:"power2.out"}}, 0);
- 出场转场: 不需要（由下一个场景的入场覆盖）
- 场景内元素交错入场: 每个元素间隔0.12-0.15s

## 视觉丰富度
- 8-12+ 个可见元素: 标题(80-120px+发光)、数据卡片(圆角+边框+大字号数字)、进度条、标签pill、装饰层、趋势箭头
- 每个场景至少2-3个装饰层: grid网格线、发光光晕、ghost text水印(3-8%透明度)、扫描线
- 颜色用 design.md 配色方案

## 动态数据具象化（每个场景必须包含以下至少3种）
- **数字冲击动画**: 核心数据出现时必须有"冲击效果"——数字从远处飞入(scale:2→1)+发光脉动(text-shadow强度0→50px→30px)+周围粒子扩散
- **数字动画**: 核心数据用GSAP countUp动画（从0到目标值，duration 1.5s），数字用JetBrains Mono 100-140px加粗
- **进度条**: 带百分比标签的圆角进度条，填充色用主色，动画从0%到目标值
- **趋势指标**: 数据旁加 ↑↓→ 箭头（绿色上涨/红色下跌），配合 +/- 百分比
- **迷你图表**: 用CSS画简易柱状图(5-7个bar)或折线，展示数据趋势
- **数据卡片网格**: 2-3个卡片并排，每个卡片含：图标、指标名、数值、变化率
- **对比条**: A vs B 双条对比，标注差值百分比

## 三层视觉结构（必须遵守）
每个场景必须有清晰的三层结构，缺一不可：
- **背景层**（z-index:0）: 深色底色#1a1a2e + grid网格 + 径向光晕 + ghost text水印
- **内容层**（z-index:1-2）: 数据卡片、标题、文字、图表等核心内容
- **装饰层**（z-index:3+）: 扫描线、粒子点、边角装饰、光效线条
三层之间必须有明确的z-index区分，不能混在一起。

## 色彩饱和度要求（禁止灰蒙蒙）
- 主色饱和度必须≥60%（HSL的S值）
- 核心数据必须用高亮色（金色#FFD700/青色#00D4FF/紫色#A855F7），不能用灰色
- 卡片边框必须有颜色（rgba(主色, 0.3)），不能用白色/灰色边框
- 每个场景至少有2种不同颜色（主色+强调色）

## 布局网格（{W}x{H}，必须严格遵守）
- 安全边距: 上下左右各100px
- 标题区: y=80-180px，左对齐或居中
- 核心内容区: y=200-750px，占画面60-70%，必须饱满
- 底部信息区: y=800-980px，放辅助数据/标签/时间线
- 左右分栏: 左60%放核心数据，右40%放辅助信息/装饰

## 动效编排（入场节奏=高级感的核心）
- **最少8个gsap.from()入场动画**，少于5个会被判定为不合格
- 入场顺序（0.12-0.15s交错）:
  1. 背景装饰层 — 先出现
  2. Ghost text水印 — 淡入
  3. 主标题 — 从上方滑入(y:-50→0)
  4. 核心数据卡片 — 从下方弹入(y:60→0, ease:back.out(1.7))
  5. 辅助元素 — 从侧面滑入
  6. 底部信息 — 最后淡入

## 禁止清单（低级感来源）
- 纯色背景无层次 / 元素无入场动画 / 静态场景无呼吸
- 所有元素同大小 / 白色浅色背景 / 元素贴边
- 无装饰层 / 文字无发光 / 口播原文大段出现在画面中
- 卡片无玻璃态(backdrop-filter:blur) / 入场无节奏
- 灰蒙蒙的画面 / 数据出现无冲击 / 只有一层结构
- 无数据可视化 / 使用linear缓动

## 视觉类型布局指引
- **data_impact**: 中心大数字(140px金色) + 环绕3-4个数据卡片 + 底部趋势条
- **dashboard**: 2x2或2x3网格卡片布局，每卡片独立数据指标
- **compare**: 左右两栏对比，中间VS分隔线
- **flow**: 水平/垂直流程图，节点+箭头连线
- **list_alert**: 左侧序号列表(3-5项)，右侧关键项高亮
- **hud**: 四角数据面板 + 中心主题 + scan line
- **quote_hero**: 中心大字金句(60-80px) + 背景氛围层
- **code_terminal**: 模拟终端窗口 + 代码行 + 闪烁光标
- **ranking_board**: 排行列表(1-5名) + 冠军高亮
- **product_showcase**: 模拟App/网页界面截图 + 标注
- **timeline_event**: 水平时间轴 + 事件节点
- **market_ticker**: K线图区域 + 涨跌幅色块

## 输出
只输出完整 HTML 代码，不要解释，不要 markdown 代码块。
在 HTML 注释中加入版本标记: <!-- vf-v5.2 -->"""


def generate_scene_html_llm(scene: dict, scene_id: int, design_md: str,
                            spec: dict, composition_id: str, W: int = 1920, H: int = 1080) -> str:
    """用 LLM 根据上游数据生成完整的场景 HTML，带重试"""
    depth_layers = scene.get("depth_layers", {})
    dl_text = ""
    if isinstance(depth_layers, dict):
        dl_text = "\n".join(f"- {k}: {v}" for k, v in depth_layers.items() if v)
    elif isinstance(depth_layers, str):
        dl_text = depth_layers

    animations = scene.get("animations", {})
    anim_text = ", ".join(f"{k}={v}" for k, v in animations.items()) if animations else ""

    key_elements = scene.get("key_elements", [])
    if isinstance(key_elements, dict):
        elems_text = ", ".join(f"{k}={v}" for k, v in list(key_elements.items())[:8])
    elif isinstance(key_elements, list):
        elems_text = ", ".join(str(e) for e in key_elements[:8])
    else:
        elems_text = str(key_elements)

    # === 反哺：读取历史质量问题，注入prompt ===
    feedback_lessons = ""
    feedback_path = Path(__file__).parent.parent.parent / "output" / "feedback_history.json"
    if feedback_path.exists():
        try:
            with open(feedback_path, "r", encoding="utf-8") as f:
                history = json.load(f)
            # 提取最近3次的高频问题
            recent = history[-3:]
            issue_counts = {}
            for entry in recent:
                for issue in entry.get("issues", []):
                    check = issue.get("check", "")
                    if check:
                        issue_counts[check] = issue_counts.get(check, 0) + 1
            if issue_counts:
                feedback_lessons = "\n## 历史质量问题（必须避免）\n"
                for check, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
                    feedback_lessons += f"- {check}: 出现{count}次，请确保本场景不出现此问题\n"
        except Exception as e:
            print(f"  ⚠️ [hf-builder] 加载反馈历史失败: {e}")

    prompt = SCENE_PROMPT.format(
        design_md=design_md[:1000],
        scene_id=scene_id,
        visual_type=scene.get("visual_type", ""),
        concept=scene.get("concept", "")[:200],
        duration=scene.get("duration", 8.0),
        depth_layers=dl_text[:400],
        density_target=scene.get("density_target", 8),
        animations=anim_text[:200],
        narration=scene.get("narration", "")[:300],
        key_elements=elems_text[:200],
        chart_type=scene.get("chart_type") or "null",
        camera_motion=json.dumps(scene.get("camera_motion")) if scene.get("camera_motion") else "null",
        composition_id=composition_id,
        W=W,
        H=H,
    ) + feedback_lessons

    system = "你是 HyperFrames 视频合成专家。只输出完整 HTML 代码，不输出任何其他文本。"

    # 第一次尝试
    response = call_llm(prompt, system, max_tokens=12000)
    html = _extract_html(response)
    if html:
        html = _auto_fix_html(html, composition_id)
        html = _fix_truncated_html(html, composition_id)
        if _validate_html(html, composition_id) and len(html) > 2500:
            return html

    # 第二次尝试（简化 prompt + 更多 token）
    print(f"    🔄 [Scene {scene_id}] 第一次生成质量不足({len(html) if html else 0} chars)，重试...", flush=True)
    simple_prompt = f"""为视频场景写完整 HTML。scene_id={scene_id}, composition_id="{composition_id}", {W}x{H}。

场景内容：{scene.get("concept", "")[:150]}
口播参考（仅供理解语义，禁止原文放入画面）：{scene.get("narration", "")[:200]}
关键数据：{elems_text[:150]}
配色：{design_md[:600]}

要求：
- 深色背景#1a1a2e，所有样式用内联style=""
- 标题80-120px+text-shadow发光
- 数据卡片(圆角边框+大字号数字)+进度条+标签
- 装饰层: grid网格、光晕、ghost text
- **至少8个tl.from()入场动画**(交错0.15s)+卡片呼吸感(repeat:-1,yoyo:true)
- 注册到 window.__timelines["{composition_id}"]
- 禁止: <style>块、CSS class、Google Fonts、Math.random()、出场动画、CSS opacity:0（用GSAP from控制）

只输出完整HTML，不要解释。"""
    response = call_llm(simple_prompt, system, max_tokens=16000)
    html = _extract_html(response)
    if html:
        html = _auto_fix_html(html, composition_id)
        html = _fix_truncated_html(html, composition_id)
        if _validate_html(html, composition_id):
            return html

    # 第三次尝试（极简 prompt，最少要求）
    print(f"    🔄 [Scene {scene_id}] 第二次也不行({len(html) if html else 0} chars)，第三次...", flush=True)
    minimal_prompt = f"""Write complete HTML for a {W}x{H} video scene.
composition_id="{composition_id}"
Content (for context only, do NOT display as text): {scene.get("narration", "")[:150]}
Background: #1a1a2e, all styles inline.
Include: GSAP CDN, gsap.timeline(paused:true), window.__timelines registration.
Include: title, data cards, decorative layers.
Only output HTML code."""
    response = call_llm(minimal_prompt, system, max_tokens=16000)
    html = _extract_html(response)
    if html:
        html = _auto_fix_html(html, composition_id)
        html = _fix_truncated_html(html, composition_id)
        if _validate_html(html, composition_id):
            return html

    print(f"    ⚠️ [Scene {scene_id}] 三次都失败，用 fallback", flush=True)
    return ""


def _extract_html(response: str) -> str:
    """从 LLM 响应中提取 HTML，过滤掉 reasoning 文本"""
    if not response:
        return ""
    # 尝试 ```html...```
    m = re.search(r'```html\s*(.*?)\s*```', response, re.DOTALL)
    if m:
        return m.group(1).strip()
    # 尝试 <!DOCTYPE html>...</html>
    m = re.search(r'<!DOCTYPE html>.*?</html>', response, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(0).strip()
    # 尝试 <html>...</html>
    m = re.search(r'<html[^>]*>.*?</html>', response, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(0).strip()
    # 如果包含 <html 标签，截取到最后一个 </html>
    if '<html' in response.lower():
        start = response.lower().find('<html')
        end = response.lower().rfind('</html>')
        if end > start:
            return response[start:end+7].strip()
        return response[start:].strip()
    # 不是 HTML
    return ""


def _validate_html(html: str, composition_id: str) -> bool:
    """验证 HTML 是否符合 HyperFrames 基本要求"""
    checks = {
        'data-composition-id': 'data-composition-id' in html,
        'data-width/height': 'data-width' in html and 'data-height' in html,
        'gsap': 'gsap' in html.lower(),
        '__timelines': '__timelines' in html,
        'div': '<div' in html.lower(),
        'scene': '.scene' in html or 'class="scene"' in html or "class='scene'" in html or 'class=scene' in html or 'scene' in html.lower(),
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"      ❌ 验证失败: {failed}", flush=True)
        return False

    # 动画丰富度检查（核心：没有动画=没有灵魂）
    gsap_from_count = len(re.findall(r'\.from\(', html))
    if gsap_from_count < 3:
        print(f"      ⚠️ GSAP动画不足: {gsap_from_count} < 3，场景会很静态", flush=True)
        return False

    return True


def _fix_truncated_html(html: str, composition_id: str) -> str:
    """修复被截断的 HTML（LLM 输出超长被 max_tokens 截断）"""
    if html.strip().endswith('</html>'):
        return html  # 完整，不需要修复

    print(f"    ⚠️ HTML 被截断，尝试修复...", flush=True)

    # 1. 如果在 JS 中间被截断，移除不完整的 JS 块
    # 找到最后一个完整的 </script>
    last_script_close = html.rfind('</script>')
    if last_script_close > 0:
        # 保留到最后一个 </script>，丢弃后面的不完整内容
        html = html[:last_script_close + len('</script>')]
    else:
        # 没有 </script>，说明整个 script 块都不完整
        last_script_open = html.rfind('<script')
        if last_script_open > 0:
            html = html[:last_script_open]

    # 2. 确保有 __timelines 注册
    if '__timelines' not in html:
        html += f'''
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<script>
  window.__timelines = window.__timelines || {{}};
  window.__timelines["{composition_id}"] = gsap.timeline({{paused:true}});
</script>'''

    # 3. 确保有 </body></html>
    if '</body>' not in html:
        html += '\n</body>'
    if '</html>' not in html:
        html += '\n</html>'

    return html


def _auto_fix_html(html: str, composition_id: str) -> str:
    """自动修复 LLM 生成的 HTML 中的常见问题"""

    # 1. 修复 html 标签 — 添加 data 属性
    if 'data-composition-id' not in html:
        html = re.sub(
            r'<html[^>]*>',
            f'<html data-composition-id="{composition_id}" data-width="{_VIDEO_W}" data-height="{_VIDEO_H}">',
            html, count=1
        )

    # 2. 添加 GSAP CDN（如果缺少）
    if 'gsap.min.js' not in html:
        html = html.replace('</head>',
            '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>\n</head>')

    # 3. 如果完全没有 gsap.timeline，注入完整动画
    if 'gsap.timeline' not in html:
        animation_code = _generate_default_animations(composition_id)
        last_script_end = html.rfind('</script>')
        if last_script_end > 0:
            html = html[:last_script_end] + animation_code + '\n' + html[last_script_end:]
        else:
            html += animation_code

    # 4. 添加 __timelines 注册（如果缺少）
    if '__timelines' not in html:
        tl_match = re.search(r'(const|let|var)\s+(\w+)\s*=\s*gsap\.timeline', html)
        tl_name = tl_match.group(2) if tl_match else "tl"
        register_code = f'''
      window.__timelines = window.__timelines || {{}};
      window.__timelines["{composition_id}"] = {tl_name};'''
        last_script_end = html.rfind('</script>')
        if last_script_end > 0:
            html = html[:last_script_end] + register_code + '\n    ' + html[last_script_end:]

    # 5. 移除 Google Fonts（sandbox 渲染会失败）
    html = re.sub(r'<link[^>]*fonts\.googleapis\.com[^>]*>', '', html)
    html = re.sub(r'@import\s+url\([^)]*fonts\.googleapis\.com[^)]*\)\s*;?', '', html)

    # 6. 移除禁止项
    html = re.sub(r'gsap\.utils\.random\([^)]*\)', '50', html)
    # repeat:-1 保留！呼吸动画需要无限重复（SCENE_PROMPT明确要求）
    html = re.sub(r'Math\.random\(\)', '0.5', html)
    html = re.sub(r'Math\.random\(\)\s*\*\s*(\d+)', r'Math.floor(\1/2)', html)

    # 6c. 修复 LLM 把 repeat:-1 "纠正"为 repeat:0 的问题
    # 有 yoyo:true 的动画应该是无限循环的呼吸动画
    html = re.sub(r'repeat:\s*0\s*,\s*yoyo:\s*true', 'repeat: -1, yoyo: true', html)
    html = re.sub(r'repeat:\s*0\s*,\s*yoyo:\s*True', 'repeat: -1, yoyo: true', html)

    # 6b. CSS animation infinite → finite（避免 HF 渲染卡住）
    html = re.sub(r'animation-iteration-count:\s*infinite', 'animation-iteration-count: 3', html)
    html = re.sub(r'animation:\s*([^;{}]*?)\s+infinite', r'animation: \1 3', html)
    
    # 6d. GSAP 复杂度限制（防止 "Set maximum size exceeded"）
    # 限制 repeat:-1 的数量（最多4个呼吸动画）
    repeat_count = len(re.findall(r'repeat:\s*-1', html))
    if repeat_count > 4:
        # 保留前4个，后面的 repeat:-1 改为 repeat:0（只播放一次）
        count = 0
        def _limit_repeat(m):
            nonlocal count
            count += 1
            if count <= 4:
                return m.group(0)
            return 'repeat: 0'
        html = re.sub(r'repeat:\s*-1', _limit_repeat, html)
        print(f"      ⚠️ [auto-fix] 呼吸动画过多({repeat_count})，已限制为4个", flush=True)
    
    # 限制 gsap.to 的数量（最多10个，超出的注释掉）
    gsap_to_count = len(re.findall(r'(?<!//\s)tl\.to\(|(?<!//\s)gsap\.to\(', html))
    if gsap_to_count > 10:
        print(f"      ⚠️ [auto-fix] gsap.to过多({gsap_to_count})，需要简化", flush=True)

    # 1. 移除 subtitle-keywords div（用sed逐行处理，更可靠）
    lines = html.split('\n')
    new_lines = []
    skip_until_close = False
    for line in lines:
        if 'subtitle-keywords' in line.lower() or 'subtitle keywords' in line.lower():
            skip_until_close = True
            continue
        if skip_until_close:
            if '</div>' in line:
                skip_until_close = False
            continue
        new_lines.append(line)
    html = '\n'.join(new_lines)
    
    # 2. 移除 Subtitle Keywords 注释
    html = re.sub(r'<!--\s*Subtitle\s*Keywords\s*-->\s*', '', html)
    
    # 3. 移除相关的 GSAP 动画代码（// 3. Subtitle Keywords...）
    html = re.sub(r'//\s*3\.\s*Subtitle\s*Keywords[^\n]*\n[^\n]*(?:\n(?!\s*//)[^\n]*)*', '', html)

    # 7. 移除 CSS 中的中文注释
    html = re.sub(r'/\*[^*]*[\u4e00-\u9fff][^*]*\*/', '', html)

    # 8. 替换 CSS 变量为硬编码值（HF 沙箱可能不支持 CSS 自定义属性）
    css_var_map = {
        "var(--bg-color)": "#1a1a2e",
        "var(--background)": "#1a1a2e",
        "var(--bg)": "#1a1a2e",
        "var(--primary-color)": "#00D4FF",
        "var(--primary)": "#00D4FF",
        "var(--accent-color)": "#FF6B6B",
        "var(--accent)": "#FF6B6B",
        "var(--text-color)": "#FFFFFF",
        "var(--text)": "#FFFFFF",
        "var(--text-secondary)": "#A0A0B0",
        "var(--secondary)": "#A0A0B0",
        "var(--data-color)": "#4ECDC4",
        "var(--data)": "#4ECDC4",
        "var(--gold)": "#FFD700",
        "var(--success)": "#00FF88",
        "var(--warning)": "#FFD700",
        "var(--danger)": "#FF4444",
        "var(--font-body)": "'Inter','Noto Sans SC',sans-serif",
        "var(--font-headline)": "'Inter','Noto Sans SC',sans-serif",
        "var(--font-data)": "'JetBrains Mono',monospace",
        "var(--md-radius)": "12px",
        "var(--sm-radius)": "8px",
        "var(--rounded-md)": "12px",
        "var(--rounded-sm)": "8px",
        "var(--rounded-lg)": "16px",
    }
    for var, val in css_var_map.items():
        html = html.replace(var, val)

    # 9. 也替换 :root 中的 CSS 变量定义中的 var() 引用
    # 把 :root { --bg-color: var(--xxx) } 这种链式引用也替换掉
    html = re.sub(r'--([\w-]+):\s*var\(--([\w-]+)\)',
                  lambda m: f'--{m.group(1)}: {css_var_map.get(f"var(--{m.group(2)})", "inherit")}',
                  html)

    # 10. 确保 body 有 overflow:hidden
    if 'overflow:hidden' not in html and 'overflow: hidden' not in html:
        html = re.sub(r'<body([^>]*)>', r'<body\1 style="margin:0;padding:0;overflow:hidden;">', html, count=1)

    # 11. 确保 .scene div 有内联 background（HF 沙箱独立渲染scene，不继承body背景）
    if '<div class="scene"' in html:
        scene_match = re.search(r'<div class="scene"([^>]*)>', html)
        if scene_match:
            attrs = scene_match.group(1)
            if 'style="' in attrs:
                if 'background' not in attrs:
                    # 有style但没有background → 注入
                    html = re.sub(
                        r'(<div class="scene"[^>]*style=")',
                        r'\1background:#1a1a2e;',
                        html, count=1
                    )
            else:
                # 没有 style → 添加新的
                html = html.replace('<div class="scene"', '<div class="scene" style="background:#1a1a2e;"', 1)
    # 11b. 如果没有 class="scene" 的 div，在 body 后第一个 div 上添加
    if 'class="scene"' not in html and "class='scene'" not in html and 'class=scene' not in html:
        html = re.sub(r'(<body[^>]*>)', r'\1<div class="scene" style="position:relative;width:1920px;height:1080px;background:#1a1a2e;overflow:hidden;">', html, count=1)
        html = re.sub(r'(</body>)', r'</div>\1', html, count=1)

    # 12. 确保 html 和 body 也有背景色（防止画面下半部分白色）
    html_tag_match = re.search(r'<html[^>]*>', html)
    if html_tag_match:
        html_tag = html_tag_match.group(0)
        if 'background' not in html_tag:
            if 'style="' in html_tag:
                # 已有 style → 注入 background
                new_tag = re.sub(r'(style=")', r'\1background:#1a1a2e;', html_tag, count=1)
            else:
                new_tag = html_tag.replace('>', ' style="background:#1a1a2e;">')
            html = html.replace(html_tag, new_tag, 1)
    if '<body' in html:
        body_match = re.search(r'<body[^>]*>', html)
        if body_match:
            body_tag = body_match.group(0)
            if 'background' not in body_tag:
                if 'style="' in body_tag:
                    new_body = re.sub(r'(style=")', r'\1margin:0;padding:0;overflow:hidden;background:#1a1a2e;', body_tag, count=1)
                else:
                    new_body = body_tag.replace('>', ' style="margin:0;padding:0;overflow:hidden;background:#1a1a2e;">')
                html = html.replace(body_tag, new_body, 1)

    # 13. 确保 .scene 有 min-height:100%
    if '.scene {' in html and 'min-height' not in html:
        html = html.replace('.scene {', '.scene { min-height:100%;', 1)

    # 14. 强制深色背景 — 把白色/浅色背景替换为深色
    # Replace white/light backgrounds in inline styles (both background and background-color)
    for prop in ['background', 'background-color']:
        html = re.sub(rf'{prop}:\s*#fff(fff)?(;|")', rf'{prop}:#1a1a2e\2', html, flags=re.IGNORECASE)
        html = re.sub(rf'{prop}:\s*white(;|")', rf'{prop}:#1a1a2e\1', html, flags=re.IGNORECASE)
        html = re.sub(rf'{prop}:\s*#f[0-9a-f]{{5}}(;|")', rf'{prop}:#1a1a2e\1', html, flags=re.IGNORECASE)
        html = re.sub(rf'{prop}:\s*#e[0-9a-f]{{5}}(;|")', rf'{prop}:#1a1a2e\1', html, flags=re.IGNORECASE)
        html = re.sub(rf'{prop}:\s*#d[0-9a-f]{{5}}(;|")', rf'{prop}:#1a1a2e\1', html, flags=re.IGNORECASE)
        html = re.sub(rf'{prop}:\s*rgb\(\s*2[0-4]\d\s*,\s*2[0-4]\d\s*,\s*2[0-4]\d\s*\)(;|")', rf'{prop}:#1a1a2e\1', html)
        html = re.sub(rf'{prop}:\s*rgb\(\s*25[0-5]\s*,\s*25[0-5]\s*,\s*25[0-5]\s*\)(;|")', rf'{prop}:#1a1a2e\1', html)
    # Also fix body/html backgrounds
    html = re.sub(r'(body[^>]*style="[^"]*)background:\s*#fff(fff)?', r'\1background:#1a1a2e', html, flags=re.IGNORECASE)

    # 15. 最终安全网：合并同一元素上的重复 style 属性
    html = re.sub(
        r'(style="[^"]*")\s+(style="[^"]*")',
        lambda m: m.group(1).rstrip('"') + '; ' + m.group(2)[7:-1] if m.group(2).startswith('style="') and m.group(2).endswith('"') else m.group(1) + ' ' + m.group(2),
        html
    )

    # 16. 修复opacity问题：内容元素必须默认可见
    # 装饰层关键词（这些可以保持低opacity）
    decorative_keywords = ['grid', 'glow', 'ghost', 'scan', 'particle', 'corner', 'line', 'bg-', 'background']
    content_keywords = ['card', 'title', 'data', 'content', 'text', 'number', 'value', 'label', 'tag', 'info', 'quote', 'center', 'area', 'heading', 'name', 'desc', 'stat', 'metric', 'score']

    def fix_opacity(match):
        full_tag = match.group(0)
        tag_name = match.group(1)
        attrs = match.group(2)

        is_decorative = False
        id_match = re.search(r'id="([^"]*)"', attrs)
        class_match = re.search(r'class="([^"]*)"', attrs)
        id_name = id_match.group(1).lower() if id_match else ""
        class_name = class_match.group(1).lower() if class_match else ""

        for keyword in decorative_keywords:
            if keyword in id_name or keyword in class_name:
                is_decorative = True
                break
        for keyword in content_keywords:
            if keyword in id_name or keyword in class_name:
                is_decorative = False
                break

        if not is_decorative:
            # 只替换 opacity:0（精确零），保留 opacity:0.5 等有意义的半透明
            attrs = re.sub(r'opacity:\s*0(?:\.0+)?(?=[;\s"])', 'opacity:1', attrs)

        return f'<{tag_name}{attrs}>'

    # 匹配所有HTML元素（不限于div）带有opacity:0的
    html = re.sub(
        r'<(\w+)([^>]*opacity:\s*0[^>]*)>',
        fix_opacity,
        html
    )

    # 移除<style>块中的opacity:0规则
    def fix_style_block(match):
        style_content = match.group(1)
        # 只替换 opacity:0（精确零），保留 opacity:0.05 等半透明值
        # lookahead确保不匹配 opacity:0.8（0后面跟非零小数）
        style_content = re.sub(r'opacity:\s*0(?=[;\s"])', 'opacity:1', style_content)
        return f'<style>{style_content}</style>'

    html = re.sub(r'<style>(.*?)</style>', fix_style_block, html, flags=re.DOTALL)

    # 最终兜底：移除所有残留的内联opacity:0（GSAP代码中的除外）
    gsap_blocks = []
    def save_gsap(m):
        gsap_blocks.append(m.group(0))
        return f'__GSAP_BLOCK_{len(gsap_blocks)-1}__'
    html = re.sub(r'<script[^>]*>.*?</script>', save_gsap, html, flags=re.DOTALL)
    # 只替换 opacity:0（精确零），保留装饰层半透明值如 opacity:0.05
    # lookahead: opacity:0 后面必须是 " 或 ; 或空白，不能是 .8 等小数
    html = re.sub(r'(style="[^"]*?)opacity:\s*0(?=[";\s])', r'\1opacity:1', html)
    for i, block in enumerate(gsap_blocks):
        html = html.replace(f'__GSAP_BLOCK_{i}__', block)

    # 9. 强制给高z-index装饰元素加pointer-events:none（防止遮挡内容）
    # 匹配 z-index:5+ 的div，如果没有pointer-events:none就加上
    def add_pointer_events(match):
        tag = match.group(0)
        if 'pointer-events' not in tag:
            # 在style属性末尾加pointer-events:none
            tag = tag.replace('"', ';pointer-events:none"', 1)
        return tag
    html = re.sub(r'<div[^>]*z-index:\s*(?:[5-9]|[1-9]\d+)[^>]*>', add_pointer_events, html)

    return html


def _generate_default_animations(composition_id: str) -> str:
    """为缺少动画的场景生成默认 GSAP 动画代码"""
    sel = f'[data-composition-id=\\"{composition_id}\\"]'
    sel_sq = f"[data-composition-id='{composition_id}']"
    return f'''
<script>
(function() {{
  var tl = gsap.timeline({{paused:true}});
  var root = document.querySelector('{sel_sq}');
  if (!root) {{ root = document; }}
  var els = root.querySelectorAll('.scene > *');
  els.forEach(function(el, i) {{
    tl.from(el, {{y:40, opacity:0, duration:0.6, ease:"power3.out"}}, i * 0.15);
  }});
  var cards = root.querySelectorAll('.card, .stat, .bar, .tag, .progress-bar');
  cards.forEach(function(el, i) {{
    tl.from(el, {{y:30, opacity:0, scale:0.9, duration:0.5, ease:"power2.out"}}, 0.3 + i * 0.1);
  }});
  window.__timelines = window.__timelines || {{}};
  window.__timelines["{composition_id}"] = tl;
}})();
</script>'''


# ============================================================
# Fallback 模板（LLM 失败时的保底）
# ============================================================

def fallback_scene_html(scene: dict, scene_id: int, design_md: str, composition_id: str) -> str:
    """LLM 失败时的 fallback — 视觉丰富的模板"""
    # 从 design.md 提取颜色
    bg = "#1a1a2e"
    primary = "#00D4FF"
    accent = "#FF6B6B"
    gold = "#FFD700"
    for line in design_md.split("\n"):
        if "background:" in line.lower():
            m = re.search(r'#[0-9a-fA-F]{6}', line)
            if m: bg = m.group(0)
        elif "primary:" in line.lower():
            m = re.search(r'#[0-9a-fA-F]{6}', line)
            if m: primary = m.group(0)
        elif "accent:" in line.lower():
            m = re.search(r'#[0-9a-fA-F]{6}', line)
            if m: accent = m.group(0)

    narration = scene.get("narration", "")
    # 提取口播金句作为标题（取前15字）
    title = re.sub(r'[，。！？、；：""''（）\s]', '', narration)[:15] or "场景"
    # 从口播中提取关键词标签（4-8字短词，最多5个），不显示原文
    narration_tags = []
    if narration:
        for sep in ['。', '！', '？', '，', '；', '、', '：']:
            parts = narration.split(sep)
            for p in parts:
                clean = re.sub(r'[\"\"''（）\\s]', '', p.strip())
                if 4 <= len(clean) <= 8 and clean not in narration_tags:
                    narration_tags.append(clean)
                if len(narration_tags) >= 5:
                    break
            if len(narration_tags) >= 5:
                break
    key_elements = scene.get("key_elements", [])
    concept = scene.get("concept", "")[:100]

    # 从口播内容中提取有意义的短句（按句号/逗号分割，取4-15字的短句）
    narration_phrases = []
    if narration:
        for sep in ['。', '！', '？', '，', '；', '、']:
            parts = narration.split(sep)
            for p in parts:
                clean = p.strip()
                if 4 <= len(clean) <= 20 and clean not in narration_phrases:
                    narration_phrases.append(clean)
                if len(narration_phrases) >= 6:
                    break
            if len(narration_phrases) >= 6:
                break

    # 从口播中提取数据点（数字+单位）
    data_points = []
    if narration:
        for m in re.finditer(r'([\d,.]+)\s*(万|亿|%|倍|秒|分钟|小时|个|人|次|元|块)', narration):
            data_points.append((m.group(0), m.group(2)))

    # 合并：口播短句 + key_elements 作为卡片内容来源
    card_items = []
    # 优先用口播中的数据点
    for val, unit in data_points[:2]:
        card_items.append({"num": val, "label": f"({unit})"})
    # 再用口播短句填充
    for phrase in narration_phrases:
        if len(card_items) >= 4:
            break
        # 提取短句中的关键词作为标签
        card_items.append({"num": phrase[:6], "label": phrase[6:18] if len(phrase) > 6 else ""})
    # 如果还不够，用 key_elements 补充
    for elem in key_elements:
        if len(card_items) >= 4:
            break
        elem_str = str(elem)
        m = re.search(r'([\d,.]+)\s*(万|亿|%|倍)?', elem_str)
        num = m.group(0) if m else elem_str[:8]
        label = re.sub(r'[\d,.]+[万亿%倍]?[+~]?\s*', '', elem_str).strip()[:12] or ""
        card_items.append({"num": num, "label": label})

    # 数据卡片（玻璃拟态风格）
    cards = ""
    card_colors = ["#06b6d4", "#7c3aed", "#C9A96E", "#00FF88", "#FF00FF", "#FF6B6B"]
    for i, item in enumerate(card_items[:4]):
        num = item.get("num", "")
        label = item.get("label", "")
        c = card_colors[i % len(card_colors)]
        cards += f'''<div class="card" style="flex:1;background:rgba(10,10,10,0.7);border:1px solid {c}40;border-radius:16px;padding:28px 20px;text-align:center;position:relative;overflow:hidden;backdrop-filter:blur(10px);">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,{c},{c}60);border-radius:16px 16px 0 0;"></div>
          <div style="position:absolute;top:0;left:0;right:0;bottom:0;background:radial-gradient(ellipse at top,{c}08,transparent 70%);pointer-events:none;"></div>
          <div class="stat" style="font-size:42px;font-weight:900;color:{c};font-family:'JetBrains Mono','Noto Sans SC',monospace;text-shadow:0 0 20px {c}40;">{num}</div>
          <div style="font-size:13px;color:#A0A0B0;margin-top:10px;letter-spacing:1px;">{label}</div>
        </div>'''

    # 进度条（用口播短句）
    progress = ""
    for i in range(min(3, len(narration_phrases))):
        pct = [78, 62, 45][i]
        c = card_colors[i]
        lbl = narration_phrases[i][:12]
        progress += f'''<div style="margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;font-size:13px;color:#A0A0B0;margin-bottom:6px;"><span>{lbl}</span><span style="color:{c};font-family:'JetBrains Mono',monospace;">{pct}%</span></div>
          <div style="width:100%;height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;"><div class="bar" style="width:{pct}%;height:100%;background:linear-gradient(90deg,{c},{c}60);border-radius:3px;box-shadow:0 0 8px {c}40;"></div></div>
        </div>'''

    # 标签（从口播中提取关键词）
    tags = ""
    tag_words = []
    if narration:
        # 提取4-6字的关键词
        for kw in re.findall(r'[\u4e00-\u9fff]{2,6}', narration):
            if kw not in tag_words and len(kw) >= 2:
                tag_words.append(kw)
            if len(tag_words) >= 5:
                break
    if not tag_words:
        tag_words = ["2026", "实时", "数据", "AI", "热点"]
    tag_colors = ["#06b6d4", "#7c3aed", "#C9A96E", "#00FF88", "#FF6B6B"]
    for j, word in enumerate(tag_words[:5]):
        c = tag_colors[j % len(tag_colors)]
        tags += f'<span class="tag" style="display:inline-block;padding:5px 14px;border-radius:20px;background:{c}12;border:1px solid {c}30;font-size:12px;color:{c};margin:3px;letter-spacing:1px;">{word}</span>'

    return f'''<!DOCTYPE html>
<html data-composition-id="{composition_id}" data-width="1920" data-height="1080" style="background:#1a1a2e;">
<head><meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:#0a0a0a;font-family:'Inter','Noto Sans SC',sans-serif;">
<div class="scene" style="position:relative;width:1920px;height:1080px;background:#1a1a2e;overflow:hidden;">

  <!-- Layer 0: Grid pattern -->
  <div style="position:absolute;top:0;left:0;width:100%;height:100%;background-image:linear-gradient(rgba(6,182,212,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(6,182,212,0.03) 1px,transparent 1px);background-size:60px 60px;opacity:0.5;"></div>

  <!-- Layer 1: Glow orbs -->
  <div style="position:absolute;top:-20%;right:-10%;width:600px;height:600px;background:radial-gradient(circle,{primary}15,transparent 70%);border-radius:50%;filter:blur(60px);"></div>
  <div style="position:absolute;bottom:-20%;left:-10%;width:500px;height:500px;background:radial-gradient(circle,{accent}10,transparent 70%);border-radius:50%;filter:blur(60px);"></div>

  <!-- Layer 2: Ghost text watermark -->
  <div class="ghost-text" style="position:absolute;font-size:240px;font-weight:900;color:{primary}05;top:50%;left:50%;transform:translate(-50%,-50%);pointer-events:none;white-space:nowrap;font-family:'JetBrains Mono',monospace;">{title[:4]}</div>

  <!-- Layer 3: Scan line -->
  <div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,{primary}60,transparent);animation:scan 4s linear infinite;pointer-events:none;z-index:10;"></div>

  <!-- Content -->
  <div style="position:relative;z-index:5;padding:80px 100px;height:100%;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;gap:28px;">

    <!-- Title bar -->
    <div style="display:flex;align-items:center;gap:16px;">
      <div style="width:5px;height:56px;background:linear-gradient(180deg,{primary},{accent});border-radius:3px;"></div>
      <h1 class="title" style="font-size:88px;font-weight:900;color:#fff;margin:0;text-shadow:0 0 30px {primary}60,0 0 60px {primary}30;line-height:1.1;">{title}</h1>
    </div>

    <!-- Keyword tags from narration (not the full text) -->
    {''.join(f'<span class="tag-pill" style="display:inline-block;padding:4px 14px;margin:0 6px 6px 0;border-radius:20px;background:{primary}15;border:1px solid {primary}30;font-size:16px;color:{primary};">{t}</span>' for t in narration_tags) if narration_tags else ''}

    <!-- Data cards row -->
    <div style="display:flex;gap:20px;margin-top:8px;">{cards}</div>

    <!-- Progress bars + Tags row -->
    <div style="display:flex;gap:60px;align-items:flex-start;">
      <div style="flex:1;max-width:500px;">{progress}</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;">{tags}</div>
    </div>
  </div>
</div>

<style>
@keyframes scan {{ from{{top:0}} to{{top:100%}} }}
</style>
<script>
(function() {{
  var cid = "{composition_id}";
  var tl = gsap.timeline({{paused:true}});
  tl.from("[data-composition-id=" + cid + "] .ghost-text", {{scale:0.8, opacity:0, duration:1.2, ease:"power3.out"}}, 0);
  tl.from("[data-composition-id=" + cid + "] .title", {{y:60, opacity:0, duration:0.7, ease:"power3.out"}}, 0.2);
  tl.from("[data-composition-id=" + cid + "] .quote", {{y:30, opacity:0, duration:0.5, ease:"power2.out"}}, 0.4);
  tl.from("[data-composition-id=" + cid + "] .card", {{y:40, opacity:0, scale:0.9, duration:0.5, stagger:0.1, ease:"back.out(1.5)"}}, 0.5);
  // 数字冲击效果：第一个数字从2.5倍放大→缩小
  tl.from("[data-composition-id=" + cid + "] .stat", {{scale:2.5, opacity:0, duration:0.6, ease:"back.out(1.7)"}}, 0.6);
  gsap.to("[data-composition-id=" + cid + "] .card", {{scale:1.02, duration:2.5, repeat:-1, yoyo:true, ease:"sine.inOut", stagger:0.3}});
  tl.from("[data-composition-id=" + cid + "] .bar", {{width:0, duration:0.8, ease:"power2.inOut"}}, 0.8);
  tl.from("[data-composition-id=" + cid + "] .tag", {{y:20, opacity:0, scale:0.8, duration:0.3, stagger:0.05, ease:"power2.out"}}, 1.0);
  window.__timelines = window.__timelines || {{}};
  window.__timelines[cid] = tl;
}})();
</script>
</body>
</html>'''


# ============================================================
# 主流程
# ============================================================

def validate_scene_html(html: str, scene: dict) -> bool:
    """验证场景HTML质量（纯regex，不调LLM）"""
    if not html or len(html) < 3000:
        return False
    
    import re
    
    # 检查0：版本标记（v5.1+ 新 prompt 生成的才有）
    if "vf-v5.2" not in html:
        print(f"      ⚠️ 旧版HTML（缺少 vf-v5.2 标记），需要重新生成", flush=True)
        return False
    
    # 检查CSS opacity:0（不允许在CSS中设置，但opacity:0.5等半透明值允许）
    css_opacity_count = len(re.findall(r'style="[^"]*opacity:\s*0(?=[";\s])', html))
    if css_opacity_count > 0:
        print(f"      ⚠️ CSS opacity:0过多: {css_opacity_count}个", flush=True)
        return False
    
    # 检查1：必须有GSAP动画（≥5个，对齐质量诊断阈值）
    gsap_count = len(re.findall(r'(?:gsap|tl)\.(to|from|fromTo|timeline)', html))
    if gsap_count < 5:
        print(f"      ⚠️ GSAP动画不足: {gsap_count}个 (需要≥5)", flush=True)
        return False
    
    # 检查2：必须有可见文字内容（font-size + 实际文本）
    text_elements = re.findall(r'font-size:\s*\d+px[^"]*"[^>]*>[^<]{3,}', html)
    if len(text_elements) < 2:
        print(f"      ⚠️ 文字元素不足: {len(text_elements)}个 (需要≥2)", flush=True)
        return False
    
    # 检查3：必须有背景色（深色背景）
    if '#1a1a2e' not in html and '#0a0a1a' not in html and '#16213e' not in html:
        print(f"      ⚠️ 缺少深色背景", flush=True)
        return False
    
    # 检查4：数字冲击效果（scale动画）——仅对有数字的场景强制
    # 检查场景是否包含数字元素（.stat类、数字内容、data_impact类型等）
    has_numeric = bool(re.search(r'class="[^"]*stat[^"]*"', html)) or \
                  bool(re.search(r'font-size:\s*[5-9]\d+px[^"]*">\s*\d', html)) or \
                  'data_impact' in html or 'big_number' in html
    if has_numeric and 'scale:2' not in html and 'scale:3' not in html:
        print(f"      ⚠️ 有数字元素但缺少数字冲击效果（需要scale:2.x或scale:3.x动画）", flush=True)
        return False
    
    # 检查5：必须有三层视觉结构（z-index分层）
    z_index_count = len(re.findall(r'z-index:\s*\d+', html))
    if z_index_count < 2:
        print(f"      ⚠️ 三层视觉结构不足: {z_index_count}个z-index (需要≥2)", flush=True)
        return False
    
    # 检查6：玻璃态效果（backdrop-filter）— 模板场景可以没有
    # 只对LLM生成的场景强制，模板场景通过即可
    if 'backdrop-filter' not in html and len(html) > 8000:
        print(f"      ⚠️ 缺少玻璃态效果（backdrop-filter）", flush=True)
        return False
    
    # 检查7：元素不能溢出屏幕（检查是否有overflow:hidden在scene div上）
    # scene div应该有overflow:hidden防止内容溢出
    if 'overflow:hidden' not in html[:1000] and 'overflow: hidden' not in html[:1000]:
        print(f"      ⚠️ scene div缺少overflow:hidden", flush=True)
        return False
    
    return True


def generate_and_build(scene, sid, total, ctx=None):
    """单个场景：LLM优先 → 模板兜底 → fallback"""
    ctx = ctx or {}
    design_md = ctx.get("_design_md", "")
    design_specs = ctx.get("_design_specs", {})
    spec = design_specs.get(sid, {})
    composition_id = f"beat-{sid}"
    W = ctx.get("video_width", 1920)
    H = ctx.get("video_height", 1080)
    
    # === V5: LLM优先（生成更高质量的视觉）===
    max_retries = 2
    for attempt in range(max_retries):
        html = generate_scene_html_llm(scene, sid, design_md, spec, composition_id, W, H)
        if not html:
            continue
        if validate_scene_html(html, scene):
            print(f"    ✅ [Scene {sid}] LLM生成成功")
            return sid, html
    
    # === 模板兜底（LLM失败时使用）===
    print(f"    ⚠️ [Scene {sid}] LLM失败，使用模板兜底")
    try:
        from scene_templates import generate_scene_from_template, set_design_colors
        design_dict = {}
        if spec:
            design_dict = spec
        elif design_md:
            # 从design.md提取颜色
            for line in design_md.split("\n"):
                for key in ["background", "primary", "accent", "data"]:
                    if f"{key}:" in line.lower():
                        import re as _re
                        m = _re.search(r'#[0-9a-fA-F]{6}', line)
                        if m:
                            design_dict.setdefault("colors", {})[key] = m.group(0)
        
        html = generate_scene_from_template(scene, sid, design_dict)
        if html and len(html) > 100:
            # 包裹完整HTML结构（传入scene用于scene-specific GSAP）
            full_html = _wrap_html(html, composition_id, W, H, scene=scene)
            if validate_scene_html(full_html, scene):
                print(f"    ✅ [Scene {sid}] 模板兜底成功")
                return sid, full_html
    except Exception as e:
        print(f"    ⚠️ [Scene {sid}] 模板异常: {e}")
    
    # === 最终fallback ===
    print(f"    ⚠️ [Scene {sid}] 使用硬编码fallback")
    html = fallback_scene_html(scene, sid, design_md, composition_id)
    return sid, html


def _wrap_html(body_html: str, composition_id: str, W: int = 1920, H: int = 1080, scene: dict = None) -> str:
    """将模板生成的body内容包裹成完整HTML文档
    
    如果body_html已包含GSAP脚本（模板生成的），不再注入generic GSAP。
    如果没有GSAP，根据scene的animation verbs生成scene-specific GSAP。
    """
    # 检查body_html是否已包含GSAP场景动画（不含Canvas粒子的tl.to(proxy)）
    # 只检查tl.from/tl.fromTo（入场动画），不检查tl.to(proxy)（粒子驱动）
    has_scene_gsap = bool(re.search(r'tl\.(from|fromTo)\s*\(', body_html))
    
    gsap_section = ""
    if not has_scene_gsap:
        # 根据storyboard的animation verbs生成scene-specific GSAP
        gsap_section = _generate_scene_gsap(composition_id, scene)
    
    return f'''<!DOCTYPE html>
<html data-composition-id="{composition_id}" data-width="{W}" data-height="{H}" style="background:#1a1a2e;">
<head>
<meta charset="UTF-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:#1a1a2e;">
<div style="position:relative;width:{W}px;height:{H}px;background:#1a1a2e;overflow:hidden;">
{body_html}
</div>
{gsap_section}
</body>
</html>'''


def _generate_scene_gsap(composition_id: str, scene: dict = None) -> str:
    """根据storyboard的animation verbs生成scene-specific GSAP动画"""
    animations = {}
    if scene:
        animations = scene.get("animations", {})
    
    # 默认animation verbs（如果没有storyboard数据）
    title_verb = animations.get("title", "SLAMS")
    data_verb = animations.get("data", "FLOATS")
    deco_verb = animations.get("decoration", "PULSES")
    
    # 从verb映射到GSAP参数
    verb_params = {
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
        "EXPOSES": {"from": "{x:40, opacity:0, duration:0.6, ease:'power3.out'}", "stagger": 0},
        "MATERIALIZES": {"from": "{opacity:0, scale:0.95, duration:0.8, ease:'power2.out'}", "stagger": 0.1},
        "HIGHLIGHTS": {"from": "{opacity:0, backgroundColor:'rgba(255,215,0,0.3)', duration:0.6, ease:'power2.out'}", "stagger": 0},
        "SYSTEMATIZES": {"from": "{x:-40, opacity:0, duration:0.5, ease:'power3.out'}", "stagger": 0.15},
        "INSPIRES": {"from": "{y:20, opacity:0, scale:0.98, duration:1, ease:'sine.out'}", "stagger": 0.2},
        "STRUCTURES": {"from": "{scaleX:0, opacity:0, transformOrigin:'left', duration:0.8, ease:'power2.inOut'}", "stagger": 0},
    }
    
    # 获取参数，未知verb用默认FLOATS
    t_params = verb_params.get(title_verb, verb_params["FLOATS"])
    d_params = verb_params.get(data_verb, verb_params["FLOATS"])
    
    return f'''<script>
(function() {{
    var tl = gsap.timeline({{paused:true}});
    var root = document.querySelector('[data-composition-id={composition_id}]') || document;
    // Background decorations (fade in first)
    var decos = root.querySelectorAll('[style*="pointer-events:none"]');
    decos.forEach(function(el, i) {{
        tl.from(el, {{opacity:0, duration:1.2, ease:'power1.inOut'}}, 0);
    }});
    // Title entrance (verb: {title_verb})
    var titles = root.querySelectorAll('h1, h2');
    titles.forEach(function(el, i) {{
        tl.from(el, {t_params["from"]}, 0.1 + i * 0.15);
    }});
    // Data elements (verb: {data_verb})
    var stats = root.querySelectorAll('.stat, .card, .metric');
    stats.forEach(function(el, i) {{
        tl.from(el, {d_params["from"]}, 0.3 + i * {(d_params["stagger"] or 0.1)});
    }});
    // Number impact effect for .stat elements (scale slam)
    var bigNums = root.querySelectorAll('.stat');
    bigNums.forEach(function(el, i) {{
        tl.from(el, {{scale:2.5, opacity:0, duration:0.6, ease:'back.out(1.7)'}}, 0.3 + i * 0.15);
    }});
    // Items and badges
    var items = root.querySelectorAll('.item, .badge, .tag');
    items.forEach(function(el, i) {{
        tl.from(el, {{x:-30, opacity:0, duration:0.4, ease:'power2.out'}}, 0.4 + i * 0.08);
    }});
    // Subtitle / description text
    var subs = root.querySelectorAll('.subtitle, p');
    subs.forEach(function(el, i) {{
        tl.from(el, {{y:20, opacity:0, duration:0.5, ease:'power2.out'}}, 0.5 + i * 0.1);
    }});
    window.__timelines = window.__timelines || {{}};
    window.__timelines["{composition_id}"] = tl;
}})();
</script>'''


def build_intro_html(topic: str) -> str:
    """构建片头HTML - 简单封面，晃一下就行"""
    return f'''<!DOCTYPE html>
<html data-composition-id="beat-intro" data-width="1920" data-height="1080" style="background:#1a1a2e;">
<head>
<meta charset="UTF-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;font-family:'Inter','Noto Sans SC',sans-serif;background:#1a1a2e;">
<div style="position:relative;width:1920px;height:1080px;background:#1a1a2e;display:flex;flex-direction:column;justify-content:center;align-items:center;">
    <!-- 品牌名 -->
    <div style="font-size:80px;font-weight:900;color:#FFFFFF;text-shadow:0 0 40px rgba(0,212,255,0.6);letter-spacing:15px;">不闻AI</div>
    <!-- 话题 -->
    <div style="font-size:36px;color:rgba(0,212,255,0.7);margin-top:40px;letter-spacing:5px;">{topic}</div>
</div>
<script>
(function() {{
    var tl = gsap.timeline({{paused:true}});
    tl.from("div:first-child", {{opacity:0, scale:0.9, duration:0.5, ease:"power2.out"}}, 0);
    tl.from("div:nth-child(2)", {{opacity:0, y:20, duration:0.4, ease:"power2.out"}}, 0.3);
    window.__timelines = window.__timelines || {{}};
    window.__timelines["beat-intro"] = tl;
}})();
</script>
</body>
</html>'''


def build_outro_html() -> str:
    """构建片尾HTML - 增强版（V5.2 修复：移除重复scale属性+repeat:-1，增加CTA按钮）"""
    return '''<!DOCTYPE html>
<html data-composition-id="beat-outro" data-width="1920" data-height="1080" style="background:#1a1a2e;">
<head>
<meta charset="UTF-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;font-family:'Inter','Noto Sans SC',sans-serif;background:#1a1a2e;">
<div style="position:relative;width:1920px;height:1080px;background:#1a1a2e;display:flex;flex-direction:column;justify-content:center;align-items:center;">
    <!-- 网格背景 -->
    <div style="position:absolute;top:0;left:0;width:100%;height:100%;background:
        linear-gradient(rgba(0,102,255,0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,102,255,0.06) 1px, transparent 1px),
        radial-gradient(circle at 50% 50%, rgba(0,102,255,0.1) 0%, transparent 50%);
        background-size: 80px 80px, 80px 80px, 100% 100%;z-index:0;pointer-events:none;"></div>
    <!-- Ghost text -->
    <div id="ghost-end" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:200px;font-weight:700;color:rgba(255,255,255,0.02);z-index:0;white-space:nowrap;pointer-events:none;">END</div>
    <!-- 径向光晕 -->
    <div style="position:absolute;top:0;left:0;width:100%;height:100%;background:radial-gradient(circle at 50% 40%, rgba(0,102,255,0.15) 0%, transparent 60%);z-index:0;pointer-events:none;"></div>
    <!-- 品牌名 -->
    <div id="brand-name" style="position:relative;z-index:1;font-size:80px;font-weight:900;color:#FFFFFF;text-shadow:0 0 40px rgba(255,122,46,0.6);letter-spacing:15px;">不闻AI</div>
    <!-- 品牌标语 -->
    <div id="brand-title" style="position:relative;z-index:1;font-size:100px;font-weight:900;background:linear-gradient(135deg,#A855F7,#FFFFFF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-shadow:none;letter-spacing:10px;margin-top:30px;">癫狂吧世界</div>
    <!-- 关注按钮 -->
    <div id="cta-btn" style="position:relative;z-index:1;margin-top:50px;padding:18px 60px;background:linear-gradient(135deg,#FF7A2E,#FF5E13);border-radius:50px;font-size:28px;font-weight:700;color:#FFFFFF;letter-spacing:3px;box-shadow:0 0 30px rgba(255,122,46,0.4);">点击关注</div>
    <!-- 底部小字 -->
    <div id="follow-hint" style="position:relative;z-index:1;font-size:22px;color:rgba(255,255,255,0.5);margin-top:30px;">不错过每期精彩</div>
</div>
<script>
(function() {
    var tl = gsap.timeline({paused:true});
    tl.from("#brand-name", {opacity:0, y:-30, duration:0.5, ease:"power2.out"}, 0);
    tl.from("#brand-title", {opacity:0, scale:0.9, duration:0.6, ease:"power2.out"}, 0.2);
    tl.from("#cta-btn", {opacity:0, scale:0.8, duration:0.5, ease:"back.out(1.7)"}, 0.6);
    tl.from("#follow-hint", {opacity:0, y:15, duration:0.4, ease:"power2.out"}, 0.9);
    // 按钮呼吸（有限次数）
    tl.to("#cta-btn", {scale:1.05, duration:1.5, yoyo:true, repeat:1, ease:"sine.inOut"}, 1.2);
    window.__timelines = window.__timelines || {};
    window.__timelines["beat-outro"] = tl;
})();
</script>
</body>
</html>'''


def build_index_html(scenes: list, topic: str = "") -> str:
    """构建 index.html — 所有场景在同一 track 顺序播放，只有片尾"""
    beats = ''
    t = 0.0
    
    # 主体场景（没有片头）
    for i, scene in enumerate(scenes):
        sid = i + 1
        dur = scene.get('duration', 8.0)
        beats += f'''
      <div id="beat-{sid}" class="clip"
           data-composition-id="beat-{sid}"
           data-composition-src="compositions/beat-{sid}.html"
           data-start="{t}"
           data-duration="{dur}"
           data-track-index="0"
           data-width="1920"
           data-height="1080">
      </div>'''
        t += dur
    
    # 片尾 - 癫狂吧世界 (5秒，按design.md规范)
    outro_dur = 5.0
    beats += f'''
      <div id="beat-outro" class="clip"
           data-composition-id="beat-outro"
           data-composition-src="compositions/beat-outro.html"
           data-start="{t}"
           data-duration="{outro_dur}"
           data-track-index="0"
           data-width="1920"
           data-height="1080">
      </div>'''
    t += outro_dur

    return f'''<!doctype html>
<html>
<body>
  <div id="root" data-composition-id="main" data-start="0"
       data-duration="{t}" data-width="1920" data-height="1080">
{beats}
  </div>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    const mainTl = gsap.timeline({{ paused: true }});
    window.__timelines = window.__timelines || {{}};
    window.__timelines["main"] = mainTl;
  </script>
</body>
</html>'''


def run(context: dict) -> dict:
    """hf_builder 主入口"""
    project_root = Path(context.get("project_root", Path(__file__).parent.parent.parent))
    output_dir = project_root / "output"
    hf_dir = project_root / "hf_render_project"
    
    # 视频分辨率（支持横屏/竖屏）
    global _VIDEO_W, _VIDEO_H
    _VIDEO_W = context.get("video_width", 1920)
    _VIDEO_H = context.get("video_height", 1080)
    W, H = _VIDEO_W, _VIDEO_H
    if W != 1920 or H != 1080:
        print(f"[hf_builder] 竖屏模式: {W}x{H}")

    design_md = load_design_system(project_root)
    design_specs = load_design_specs(project_root)
    context["_design_md"] = design_md
    context["_design_specs"] = design_specs
    print(f"[hf_builder] design.md: {len(design_md)} chars | specs: {len(design_specs)} scenes")

    sb_path = context.get("storyboard_path") or str(output_dir / "storyboard.json")
    with open(sb_path, encoding="utf-8") as f:
        storyboard = json.load(f)
    scenes = storyboard if isinstance(storyboard, list) else storyboard.get("scenes", [])
    total = len(scenes)
    print(f"[hf_builder] {total} scenes from {sb_path}")

    topic = context.get("topic") or context.get("topic_data", {}).get("selected_topic") or ""
    topic_keywords = set(topic.replace("：", " ").replace("，", " ").replace("、", " ").split())
    # Common off-topic keywords to detect content pollution
    # 排除当前话题的关键词（避免误判）
    off_topic_patterns = ["存款", "居民存款", "缩水", "状元", "高分", "世界杯", "乌龙球"]
    off_topic_patterns = [kw for kw in off_topic_patterns if kw not in topic_keywords]

    compositions_dir = hf_dir / "compositions"
    compositions_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查已有场景，只重生成需要的
    existing_scenes = {}
    scenes_to_build = []
    for i, scene in enumerate(scenes):
        sid = i + 1
        html_path = compositions_dir / f"beat-{sid}.html"
        if html_path.exists():
            html = html_path.read_text(encoding="utf-8")
            if validate_scene_html(html, scene):
                existing_scenes[sid] = html
                print(f"  ⏭️ [Scene {sid}] 已存在且通过验证，跳过", flush=True)
            else:
                scenes_to_build.append((i, scene))
                print(f"  🔄 [Scene {sid}] 已存在但未通过验证，重新生成", flush=True)
        else:
            scenes_to_build.append((i, scene))
    
    # 只删除需要重新生成的场景文件
    for i, scene in scenes_to_build:
        sid = i + 1
        html_path = compositions_dir / f"beat-{sid}.html"
        if html_path.exists():
            html_path.unlink()

    print(f"[hf_builder] LLM 生成中 (串行模式, 需生成{len(scenes_to_build)}个场景)...")
    results = dict(existing_scenes)
    # Build a sid→scene map so we can access scene in the as_completed loop
    scene_map = {i+1: scene for i, scene in enumerate(scenes)}
    if scenes_to_build:
        # 串行执行避免内存溢出（BGM生成已占大量VRAM）
        # V5.2 Fix B: 场景间加3s间隔，防连续触发限流
        for i, scene in scenes_to_build:
            sid = i + 1
            if i > 0:  # 第一个场景不需要等待
                print(f"  ⏳ [hf_builder] 场景间隔 3s（防限流）...", flush=True)
                time.sleep(3)
            try:
                sid, html = generate_and_build(scene, sid, total, context)
                results[sid] = html
                with open(compositions_dir / f"beat-{sid}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                src = "LLM" if len(html) > 3000 else "fallback"
                print(f"  ✅ [{sid}/{total}] {src} {len(html)} chars", flush=True)

                # Content validation: check for off-topic pollution
                polluted = [kw for kw in off_topic_patterns if kw in html]
                if polluted:
                    print(f"  ⚠️  [{sid}/{total}] 检测到旧话题内容: {polluted}，使用fallback重新生成", flush=True)
                    fallback_html = _generate_fallback_html(scene_map[sid], context)
                    with open(compositions_dir / f"beat-{sid}.html", "w", encoding="utf-8") as f:
                        f.write(fallback_html)
                    print(f"  ✅ [{sid}/{total}] fallback {len(fallback_html)} chars", flush=True)
            except Exception as e:
                print(f"  ❌ [{sid}/{total}] {e}", flush=True)

    # 生成片尾HTML（没有片头）
    compositions_dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    outro_html = build_outro_html()
    with open(compositions_dir / "beat-outro.html", "w", encoding="utf-8") as f:
        f.write(outro_html)
    print(f"[hf_builder] 片尾已生成")
    
    # index.html
    hf_dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    index_html = build_index_html(scenes, topic)
    with open(hf_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"[hf_builder] index.html: {len(index_html)} chars")

    # 渲染由video_renderer统一负责，hf_builder只生成HTML
    context["hf_project_dir"] = str(hf_dir)
    context["compositions_dir"] = str(compositions_dir)
    return context


if __name__ == "__main__":
    ctx = {
        "project_root": str(Path(__file__).parent.parent.parent),
        "topic": "测试话题",
    }
    result = run(ctx)
    print(f"\nResult: {result.get('rendered_video', 'no output')}")

def _generate_fallback_html(scene: dict, context: dict) -> str:
    """Wrapper for fallback_scene_html that extracts parameters from context"""
    scene_id = scene.get("scene_id", 1)
    design_md = context.get("_design_md", "")
    composition_id = f"beat-{scene_id}"
    return fallback_scene_html(scene, scene_id, design_md, composition_id)
