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
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# LLM
# ============================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from llm_utils import call_llm as _shared_call_llm

def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 12000) -> str:
    return _shared_call_llm(prompt, system_prompt, max_tokens, timeout=300)


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
10. 字体: 'Inter','Noto Sans SC',sans-serif | 数据: 'JetBrains Mono',monospace
11. 背景必须深色 #1a1a2e，禁止白色/浅色
12. 不要用 Google Fonts
13. CSS 注释中不能有中文字符

## GSAP动画正确写法（严格遵守）
```javascript
// ✅ 正确：CSS中不写opacity，用GSAP控制
// HTML: <div id="el" style="color:white;">内容</div>
tl.from("#el", {{opacity: 0, y: 50, duration: 0.8}});  // GSAP自动从0动画到1

// ❌ 错误：在CSS中写opacity:0（渲染器不执行GSAP时内容完全不可见！）
// <div style="opacity: 0; color:white;">内容</div>  ← 绝对禁止！
```
**记住：CSS中的opacity只写1或不写。GSAP的from()会自动处理从0到1的动画。**

## 视觉丰富度
- 6-8+ 个可见元素: 标题(80-120px+发光)、数据卡片(圆角+边框+大字号数字)、进度条、标签pill、装饰层
- 每个场景至少2-3个装饰层: grid网格线、发光光晕、ghost text水印(3-8%透明度)、扫描线
- 颜色用 design.md 配色方案

## 布局网格（{W}x{H}，必须严格遵守）
- 安全边距: 上下左右各100px
- 标题区: y=80-180px，左对齐或居中
- 核心内容区: y=200-750px，占画面60-70%，必须饱满
- 底部信息区: y=800-980px，放辅助数据/标签/时间线
- 左右分栏: 左60%放核心数据，右40%放辅助信息/装饰
- 禁止元素松散堆砌——每个元素必须有明确的网格位置

## 视觉层次（从大到小，从亮到暗）
- 主标题: 80-120px, 主色+发光(text-shadow 0 0 30px)，最亮
- 核心数据: 100-140px, 金色/强调色, JetBrains Mono, 加粗
- 副标题/标签: 24-36px, 主色50%透明度
- 关键词标签: 20-28px, 主色70%透明度, pill样式
- 辅助文字: 16-20px, 灰色#666-#999
- Ghost text: 200-300px, 白色3-5%透明度，作为背景水印

## 动效编排（入场节奏=高级感的核心，动画数量是硬指标）
- **最少8个gsap.from()入场动画**，少于5个会被判定为不合格并重试
- 入场顺序（必须遵守，0.15s交错）:
  1. 背景装饰层（grid、光晕）— 先出现，营造氛围
  2. Ghost text水印 — 淡入
  3. 主标题 — 从上方滑入(y:-50→0)或从左侧滑入(x:-80→0)
  4. 核心数据卡片 — 从下方弹入(y:60→0, ease:back.out(1.7))
  5. 辅助元素（标签pill、进度条）— 从侧面滑入
  6. 底部信息 — 最后淡入
- 每个元素 gsap.from() 参数:
  - 标题: {{y:-50, opacity:0, duration:0.8, ease:"power3.out"}}
  - 数据卡片: {{y:60, opacity:0, scale:0.9, duration:0.7, ease:"back.out(1.7)"}}
  - 标签pill: {{x:-30, opacity:0, duration:0.5, ease:"power2.out"}}
  - 进度条: {{scaleX:0, transformOrigin:"left", duration:1, ease:"power2.inOut"}}
  - 装饰层: {{opacity:0, duration:1.2, ease:"power1.inOut"}}

## 呼吸感（让画面"活"起来）
- 核心数据卡片: scale 1.0→1.015→1.0, duration 3s, repeat:-1, yoyo:true, ease:"sine.inOut"
- 主标题文字: text-shadow发光强度脉动, opacity 0.8→1.0→0.8, duration 2.5s
- 背景光晕: 缓慢位移或缩放, duration 8-12s, repeat:-1, ease:"none"
- 标签pill: 边框颜色脉动, duration 2s, repeat:-1
- 禁止: 所有元素同时呼吸（太乱），最多2-3个元素有呼吸动画

## 装饰层（每个场景必须有至少3层）
1. **Grid网格线**: 半透明网格(100px间距, opacity 0.05-0.12)，用linear-gradient实现
2. **径向光晕**: 核心内容背后的大型radial-gradient(400-800px)，主色10-15%透明度
3. **Ghost text**: 超大字号(200-300px)白色3-5%透明度，放关键词如"DATA"/"2万亿"/"趋势"
4. **扫描线**: 水平线从上到下缓慢移动(duration 4-6s)，宽度2px，主色20%透明度
5. **粒子点**: 5-8个2-4px的圆点，不同速度缓慢漂移(duration 6-15s)
6. **边角装饰**: 四角L形边框线(40-60px长)，主色30%透明度

## 卡片设计（数据展示的核心）
- 背景: rgba(26,26,46,0.7) + backdrop-filter:blur(10px)
- 边框: 1px solid rgba(主色, 0.3)
- 圆角: 16-24px
- 内边距: 30-40px
- 顶部高光: 3px渐变色条(主色→透明)
- 内部光晕: radial-gradient从顶部(主色8%→透明)
- 阴影: 0 8px 32px rgba(0,0,0,0.4)
- 卡片内至少有: 标签(小字灰色) + 数值(大字金色) + 趋势箭头(可选)

## 禁止清单（低级感来源）
- 纯色背景无层次 → 必须有grid+光晕+ghost text
- 元素无入场动画 → 必须gsap.from()，最少8个
- 静态场景（无呼吸动画）→ 至少2个元素有repeat:-1呼吸
- 所有元素同大小 → 必须有3级字号层次
- 白色/浅色背景 → 必须深色#1a1a2e
- 元素贴边 → 必须有100px安全边距
- 无装饰层 → 至少3层装饰
- 文字无发光 → 标题必须text-shadow
- 口播原文大段出现在画面中 → 画面内容是字幕的视觉补充，不是字幕本身。只允许关键词标签(≤15字)或标题(≤15字)
- 卡片无玻璃态 → 必须backdrop-filter:blur
- 入场无节奏 → 必须0.15s交错

## 视觉类型布局指引
- **data_impact**: 中心大数字(140px金色) + 环绕3-4个数据卡片 + 底部趋势条
- **dashboard**: 2x2或2x3网格卡片布局，每卡片独立数据指标
- **compare**: 左右两栏对比，中间VS分隔线，各栏大数字+说明
- **flow**: 水平/垂直流程图，节点+箭头连线，每节点一个步骤
- **list_alert**: 左侧序号列表(3-5项)，右侧关键项高亮放大
- **hud**: 四角数据面板 + 中心主题 + scan line扫描效果
- **quote_hero**: 中心大字金句(60-80px) + 背景氛围层 + 底部关键词标签
- **code_terminal**: 模拟终端窗口 + 代码行 + 闪烁光标
- **ranking_board**: 排行列表(1-5名) + 冠军高亮 + 动态排名变化
- **product_showcase**: 模拟App/网页界面截图 + 标注callout
- **timeline_event**: 水平时间轴 + 事件节点 + 因果连线
- **market_ticker**: K线图区域 + 涨跌幅色块 + 滚动数据条

## 数据展示规则
- key_elements中的数据型元素必须渲染为卡片（带label+value+trend箭头）
- 数值必须用JetBrains Mono字体，大字号(80-140px)
- 趋势用箭头：↑绿色/红色（取决于context）, ↓红色, →灰色
- 至少2个数据卡片，每个卡片有glass-morphism效果

## 输出
只输出完整 HTML 代码，不要解释，不要 markdown 代码块。"""


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
    elems_text = ", ".join(str(e) for e in key_elements[:8])

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
        composition_id=composition_id,
        W=W,
        H=H,
    )

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
- GSAP入场动画(交错0.15s)+卡片呼吸感(repeat:-1,yoyo:true)
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
    if gsap_from_count < 5:
        print(f"      ⚠️ GSAP动画不足: {gsap_from_count} < 5，场景会很静态", flush=True)
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
        lambda m: m.group(1).rstrip('"') + '; ' + m.group(2).lstrip('style="'),
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
    """用LLM验证场景HTML是否有实质内容"""
    if not html or len(html) < 3000:
        return False
    
    # 检查CSS opacity:0（不允许在CSS中设置，但opacity:0.5等半透明值允许）
    import re
    css_opacity_count = len(re.findall(r'style="[^"]*opacity:\s*0(?=[";\s])', html))
    if css_opacity_count > 0:
        print(f"      ⚠️ CSS opacity:0过多: {css_opacity_count}个", flush=True)
        return False
    
    # 提取关键信息
    narration = scene.get("narration", "")[:100]
    key_elements = scene.get("key_elements", [])
    key_text = ", ".join(key_elements[:3]) if key_elements else ""
    
    prompt = f"""检查这个HTML场景是否有实质内容。

场景口播：{narration}
关键元素：{key_text}

HTML长度：{len(html)}字符

判断标准：
1. 是否有可见的文字内容（不是只有背景）
2. 是否有数据卡片或标题
3. 是否有实质性的视觉元素

只回答"合格"或"不合格"，不要解释。"""
    
    try:
        result = call_llm(prompt, max_tokens=50)
        if result and "合格" in result and "不合格" not in result:
            return True
    except:
        pass
    
    # 降级检查：检查HTML是否有足够多的元素
    # 统计包含文字内容的div数量
    text_elements = re.findall(r'font-size:\s*\d+px[^"]*"[^>]*>[^<]{3,}', html)
    if len(text_elements) >= 3:
        return True
    
    return False


def generate_and_build(scene, sid, total, ctx=None):
    """单个场景：LLM 生成 HTML + 验证 + 重试"""
    ctx = ctx or {}
    design_md = ctx.get("_design_md", "")
    design_specs = ctx.get("_design_specs", {})
    spec = design_specs.get(sid, {})
    composition_id = f"beat-{sid}"
    W = ctx.get("video_width", 1920)
    H = ctx.get("video_height", 1080)
    
    max_retries = 3
    
    for attempt in range(max_retries):
        html = generate_scene_html_llm(scene, sid, design_md, spec, composition_id, W, H)
        
        if not html:
            print(f"    ⚠️ [Scene {sid}] LLM 生成失败，尝试 {attempt+1}/{max_retries}", flush=True)
            continue
        
        # 验证HTML质量
        if validate_scene_html(html, scene):
            return sid, html
        else:
            print(f"    ⚠️ [Scene {sid}] HTML质量不合格，重试 {attempt+1}/{max_retries}", flush=True)
    
    # 所有重试都失败，使用fallback
    print(f"    ⚠️ [Scene {sid}] 所有尝试失败，使用 fallback", flush=True)
    html = fallback_scene_html(scene, sid, design_md, composition_id)
    return sid, html


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
    """构建片尾HTML - 正常结尾"""
    return f'''<!DOCTYPE html>
<html data-composition-id="beat-outro" data-width="1920" data-height="1080" style="background:#1a1a2e;">
<head>
<meta charset="UTF-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;font-family:'Inter','Noto Sans SC',sans-serif;background:#1a1a2e;">
<div style="position:relative;width:1920px;height:1080px;background:#1a1a2e;display:flex;flex-direction:column;justify-content:center;align-items:center;">
    <!-- 品牌标语 -->
    <div style="font-size:100px;font-weight:900;color:#FFFFFF;text-shadow:0 0 50px rgba(255,64,129,0.6);letter-spacing:10px;">癫狂吧世界</div>
    <!-- 关注提示 -->
    <div style="font-size:32px;color:rgba(255,255,255,0.6);margin-top:50px;">关注不闻AI · 一起探索未来</div>
</div>
<script>
(function() {{
    var tl = gsap.timeline({{paused:true}});
    tl.from("div:first-child", {{opacity:0, scale:0.9, duration:0.6, ease:"power2.out"}}, 0);
    tl.from("div:nth-child(2)", {{opacity:0, y:20, duration:0.4, ease:"power2.out"}}, 0.4);
    window.__timelines = window.__timelines || {{}};
    window.__timelines["beat-outro"] = tl;
}})();
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
    
    # 片尾 - 癫狂吧世界 (3秒)
    outro_dur = 3.0
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

    topic = context.get("topic", "")
    topic_keywords = set(topic.replace("：", " ").replace("，", " ").replace("、", " ").split())
    # Common off-topic keywords to detect content pollution
    off_topic_patterns = ["存款", "居民存款", "缩水", "状元", "高分", "高考", "中考", "世界杯", "乌龙球"]

    compositions_dir = hf_dir / "compositions"
    compositions_dir.mkdir(parents=True, exist_ok=True)
    for old in compositions_dir.glob("beat-*.html"):
        old.unlink()

    print(f"[hf_builder] LLM 生成中 (max_workers=3)...")
    results = {}
    # Build a sid→scene map so we can access scene in the as_completed loop
    scene_map = {i+1: scene for i, scene in enumerate(scenes)}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(generate_and_build, scene, i+1, total, context): i+1
            for i, scene in enumerate(scenes)
        }
        for future in as_completed(futures):
            try:
                sid, html = future.result()
                results[sid] = html
                with open(compositions_dir / f"beat-{sid}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                src = "LLM" if len(html) > 3000 else "fallback"
                print(f"  ✅ [{sid}/{total}] {src} {len(html)} chars", flush=True)

                # Content validation: check for off-topic pollution
                polluted = [kw for kw in off_topic_patterns if kw in html]
                if polluted:
                    print(f"  ⚠️  [{sid}/{total}] 检测到旧话题内容: {polluted}，使用fallback重新生成", flush=True)
                    # Regenerate with fallback
                    fallback_html = _generate_fallback_html(scene_map[sid], context)
                    with open(compositions_dir / f"beat-{sid}.html", "w", encoding="utf-8") as f:
                        f.write(fallback_html)
                    print(f"  ✅ [{sid}/{total}] fallback {len(fallback_html)} chars", flush=True)

            except Exception as e:
                sid = futures[future]
                print(f"  ❌ [{sid}/{total}] {e}", flush=True)

    # 生成片尾HTML（没有片头）
    outro_html = build_outro_html()
    with open(compositions_dir / "beat-outro.html", "w", encoding="utf-8") as f:
        f.write(outro_html)
    print(f"[hf_builder] 片尾已生成")
    
    # index.html
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
