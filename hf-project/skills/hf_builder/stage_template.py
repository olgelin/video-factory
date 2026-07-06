#!/usr/bin/env python3
"""
stage_template.py — 最小脚手架

只输出 HTML 骨架（DOCTYPE / GSAP CDN / container / __timelines 注册）。
LLM 生成完整视觉（背景 + 粒子 + 扫光 + 内容 + GSAP），注入两个插槽：
  {LLM_VISUAL}  — LLM 的 [VISUAL] 段（完整场景 HTML）
  {LLM_GSAP}    — LLM 的 [GSAP] 段（入场动画）

变量:
  {id}            — composition_id ("beat-1", "beat-2", ...)
  {W}             — 画布宽（默认 1920）
  {H}             — 画布高（默认 1080）
  {dur}           — 场景时长（秒）
"""

def build_skeleton(composition_id: str, scene_duration: float, W: int = 1920, H: int = 1080) -> str:
    """生成最小 HTML 骨架。不含任何视觉元素。"""
    dur = scene_duration
    return f'''<!DOCTYPE html>
<html data-composition-id="{composition_id}" data-width="{W}" data-height="{H}" data-duration="{dur:.1f}" lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{composition_id}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:#060618;width:{W}px;height:{H}px;clip-path:inset(5%);">
{{LLM_VISUAL}}
<script>
(function(){{
  var tl = gsap.timeline({{paused:true}});
  {{LLM_GSAP}}
  window.__timelines = window.__timelines || {{}};
  window.__timelines["{composition_id}"] = tl;
  tl.play();
}})();
</script>
</body>
</html>'''
