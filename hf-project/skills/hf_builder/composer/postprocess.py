"""
composer/postprocess.py — LLM HTML 后处理 + 验证

所有场景 HTML 经过此模块统一清洗，impl.py 和 build_v13.py 共用。
"""
import re
from typing import Tuple, List


def clean(raw_html: str, root_css: str = "", scene_dur: float = 8.0) -> str:
    """清洗 LLM 输出，应用所有 auto-fix。可多次调用（已注入的步骤会跳过）。"""
    html = raw_html

    # 1. 去掉 markdown 包装
    if "```" in html:
        html = _unwrap_markdown(html)

    # 2. 注入 :root CSS 变量
    if ":root {" not in html and root_css:
        html = html.replace("<style>", f"<style>\n{root_css}\n", 1)

    # 3. 注册 timeline
    if "window.__timelines" not in html:
        html = html.replace("</script>",
            '\nwindow.__timelines=window.__timelines||{};window.__timelines["main"]=tl;\n</script>', 1)

    # 4. gsap.to → tl.to
    if _has_timeline_var(html):
        html = re.sub(r'(?<!tl\.)(?<!\.)gsap\.to\(', 'tl.to(', html)

    # 5. repeat:-1 → repeat:5（HyperFrames 硬限制）
    html = re.sub(r'repeat:\s*-1', 'repeat:5', html)

    # 6. 去掉自执行包装
    # 匹配 (function(){ ... })();  或  (function(){ ... }());
    html = re.sub(r'\(\s*function\s*\(\s*\)\s*\{', '', html, count=1)
    # 去掉末尾的 })(); 或 }());  (可能在 timeline 注入行之前)
    html = re.sub(r'\n?\s*\}\s*\(\s*\)\s*\)\s*;', '', html, count=1)
    html = re.sub(r'\n?\s*\}\s*\)\s*\(\s*\)\s*;', '', html, count=1)

    return html.strip()


def validate(html: str, scene_id: int = 0) -> Tuple[bool, List[str]]:
    """验证 HTML 是否满足 HyperFrames 渲染要求。返回 (通过, 问题列表)。"""
    issues = []

    # 结构
    if not html.strip().lower().startswith('<!doctype'):
        issues.append("缺少 DOCTYPE")
    if '<html' not in html.lower():
        issues.append("缺少 <html> 标签")
    if '</html>' not in html.lower():
        issues.append("缺少 </html> 标签")
    if '<body' not in html.lower():
        issues.append("缺少 <body> 标签")
    if '</body>' not in html.lower():
        issues.append("缺少 </body> 标签")

    # CSS 变量
    if ':root' not in html:
        issues.append("缺少 :root CSS 变量定义")

    # GSAP
    if 'gsap.timeline' not in html:
        issues.append("未创建 gsap.timeline")
    if 'window.__timelines' not in html:
        issues.append("未注册 window.__timelines")
    if 'tl.from(' in html:
        issues.append("使用了 tl.from()（应该用 gsap.set + tl.to）")
    if 'repeat:-1' in html or 'repeat: -1' in html:
        issues.append("使用了 repeat:-1（会导致 HyperFrames 崩溃）")

    # 内容（用更精确的计数）
    tl_to_count = len(re.findall(r'tl\.to\(', html))
    if tl_to_count < 5:
        issues.append(f"tl.to 动画太少（{tl_to_count}个，建议 ≥8）")

    # 卡片计数：匹配 class 中的 "card" 或 "glass" 关键词
    card_classes = len(re.findall(r'class=["\'][^"\']*\b(?:card|glass-card|data-card|metric-card)\b', html))
    if card_classes < 2:
        issues.append(f"卡片元素太少（约{card_classes}个，建议 ≥3）")

    return len(issues) == 0, issues


def extract_body(html: str) -> str:
    """从完整 HTML 中提取 <body> 内容用于 batch 嵌入。"""
    m = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    if not m:
        return html
    inner = m.group(1).strip()
    inner = re.sub(r'<div\s+id=["\']root["\'][^>]*>', '', inner, count=1)
    inner = re.sub(r'<script src="[^"]*gsap[^"]*"></script>', '', inner)
    inner = re.sub(r'\n</div>\s*$', '', inner, count=1)
    return inner.strip()


# --- internals ---

def _unwrap_markdown(text: str) -> str:
    """去掉 LLM 输出的 markdown 代码块包装。"""
    if "```html" in text:
        text = text.split("```html")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1]
    return text.strip()


def _has_timeline_var(html: str) -> bool:
    return bool(re.search(r'(?:const|var|let)\s+tl\s*=\s*gsap\.timeline', html))
