"""
V7: 分层 HTML 生成 — pro 不截断。
分 3 层生成，每层 ~2500 chars，由 generate_scene_html_llm 调用。
"""
import json

def generate_layered_html(scene, scene_id, design_md, spec, composition_id, W, H, model,
                           dl_text, anim_text, elems_text,
                           call_llm_for_html, _extract_html, _auto_fix_html, _fix_truncated_html, _validate_html,
                           SCENE_PROMPT):
    """分 3 层生成 HTML"""

    narration = scene.get("narration", "")[:200]
    concept = scene.get("concept", "")[:150]

    # ── Layer 1: 静态结构（CSS + HTML 布局，不含动画）──
    layer1_prompt = f"""生成一个 {W}x{H} 视频场景的 HTML 结构层。只写结构和样式，不要动画。

## 场景信息
- ID: {scene_id} | 概念: {concept} | 时长: {scene.get('duration', 10.0)}s
- 口播: {narration}
- 关键数据: {elems_text}

## 输出要求
1. <!DOCTYPE html>，html 标签含 data-composition-id="{composition_id}" data-width="{W}" data-height="{H}"
2. 引入 GSAP CDN: <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
3. 创建空动画骨架（后续填充）:
   var tl = gsap.timeline({{paused:true}});
   window.__timelines = window.__timelines || {{}};
   window.__timelines["{composition_id}"] = tl;
   // ANIMATIONS_HERE
4. 深色蓝紫背景(#0A0A1A→#1A0A2E 渐变) + 网格线 + 2个径向光晕(蓝+紫)
5. 标题(60-80px/发光text-shadow) + 字幕区 + 2-3张玻璃态卡片(rgba半透明边框)
6. ghost text 水印(240px/3%透明度)
7. <!-- DATA_VIZ_HERE --> 占位注释（数据可视化将插入此处）
8. 所有样式用内联 style=""，禁止 <style> 块
9. 文字在 90% 安全区内

## 配色参考
{design_md[:800]}

只输出完整 HTML，不要解释。目标 ~3000 字符。"""

    system = "你是 HTML/CSS 专家。只输出完整 HTML 代码。"
    html_l1 = call_llm_for_html(layer1_prompt, system, max_tokens=8000, model=model)
    html_l1 = _extract_html(html_l1)
    if not html_l1 or len(html_l1) < 1500:
        print(f"      [Scene {scene_id}] Layer1 失败({len(html_l1) if html_l1 else 0} chars)，回退单次", flush=True)
        return _single_fallback(scene, scene_id, design_md, spec, composition_id, W, H, model,
                                dl_text, anim_text, elems_text, call_llm_for_html, _extract_html,
                                _auto_fix_html, _fix_truncated_html, _validate_html, SCENE_PROMPT)

    print(f"      L1 结构 {len(html_l1)} chars", flush=True)

    # ── Layer 2: 数据可视化 ──
    layer2_prompt = f"""在以下 HTML 中补充数据可视化。替换 <!-- DATA_VIZ_HERE -->。

## 数据要求
- 至少 2 种数据可视化：数字冲击卡片 + 进度条 + 趋势箭头
- 数字用 JetBrains Mono 42-80px，带 text-shadow 发光
- 进度条圆角/渐变/发光边框
- 从口播提取数据，没有就创造

## 当前 HTML
```html
{html_l1[:5000]}
```

在 <!-- DATA_VIZ_HERE --> 处插入数据元素。只输出完整 HTML。"""

    html_l2 = call_llm_for_html(layer2_prompt, system, max_tokens=8000, model=model)
    html_l2 = _extract_html(html_l2)
    if html_l2 and len(html_l2) > len(html_l1):
        html_l1 = html_l2
        print(f"      L2 数据 {len(html_l1)} chars", flush=True)

    # ── Layer 3: GSAP 动画 ──
    layer3_prompt = f"""在以下 HTML 中添加 GSAP 动画。替换 // ANIMATIONS_HERE。

## 动画要求
- >=8 个 tl.from() 入场动画(stagger 0.12-0.15s, ease:power3.out/back.out(1.7))
- >=2 个呼吸动画(repeat:-1, yoyo:true, scale 1.0->1.02, ease:sine.inOut)
- 1 条光扫线: 添加 id="light-scan" 的 div，gsap.to('#light-scan', {{x:1950, duration:2.5, ease:'none', repeat:-1, repeatDelay:5}})
- 粒子漂浮: gsap.to(x/y random(-15,15), repeat:-1, yoyo)
- 数字冲击: 核心数据 scale:2.5->1 + textShadow 脉冲

## 当前 HTML
```html
{html_l1[:6000]}
```

在 // ANIMATIONS_HERE 处插入动画。保持原有结构不变。只输出完整 HTML。
禁止创建 <style> 块、CSS class 或 <link> 标签。所有样式必须用内联 style=""。"""

    html_l3 = call_llm_for_html(layer3_prompt, system, max_tokens=8000, model=model)
    html_l3 = _extract_html(html_l3)
    if html_l3 and len(html_l3) > 2500:
        html_l1 = html_l3
        print(f"      L3 动画 {len(html_l1)} chars", flush=True)

    # 最终验证
    html = _auto_fix_html(html_l1, composition_id)
    html = _fix_truncated_html(html, composition_id)
    if _validate_html(html, composition_id):
        return html

    print(f"      [Scene {scene_id}] 分层验证失败，回退单次", flush=True)
    return _single_fallback(scene, scene_id, design_md, spec, composition_id, W, H, model,
                            dl_text, anim_text, elems_text, call_llm_for_html, _extract_html,
                            _auto_fix_html, _fix_truncated_html, _validate_html, SCENE_PROMPT)


def _single_fallback(scene, scene_id, design_md, spec, composition_id, W, H, model,
                     dl_text, anim_text, elems_text, call_llm_for_html, _extract_html,
                     _auto_fix_html, _fix_truncated_html, _validate_html, SCENE_PROMPT):
    """传统单次生成（分层失败时的回退）"""
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
        W=W, H=H,
    )
    system = "你是 HyperFrames 视频合成专家。只输出完整 HTML 代码。"
    response = call_llm_for_html(prompt, system, max_tokens=12000, model=model)
    html = _extract_html(response)
    if html:
        html = _auto_fix_html(html, composition_id)
        html = _fix_truncated_html(html, composition_id)
        if _validate_html(html, composition_id) and len(html) > 2500:
            return html
    return html or ""
