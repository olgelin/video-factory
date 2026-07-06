"""
scene_templates.py — 9 种 visual_type 专属骨架模板（V5.6）
每个模板保证视觉独特性，LLM 只填充数据不发明布局。

占位符:
  {COMPOSITION_ID}  — composition id
  {W}, {H}          — 1920, 1080
  {BG}              — 背景色 #0a0a0a
  {ACCENT}          — 强调色
  {ACCENT_GLOW}     — 强调色发光 rgba
  {HEADLINE}        — 标题
  {SUBHEADLINE}     — 副标题
  {TAG1}, {TAG2}    — 标签
  {DATA_VALUE}      — 核心数据
  {DATA_LABEL}      — 数据标签
  {DATA_CHANGE}     — 变化率 +47.2%
  {ITEM1}..{ITEM5}  — 列表项
  {QUOTE}           — 金句
  {DURATION}        — 场景时长
"""

# ══════════════════════════════════════════════════════════
# 1. data_impact — 数字冲击：大数字居中 + 四周数据卡片
# ══════════════════════════════════════════════════════════
DATA_IMPACT = r'''<!DOCTYPE html>
<!-- vf-v5.6 -->
<html data-composition-id="{COMPOSITION_ID}" data-width="{W}" data-height="{H}" style="background:{BG};">
<head><meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:{BG};">
<div class="scene" style="position:relative;width:{W}px;height:{H}px;background:{BG};overflow:hidden;">

  <!-- 背景：径向光晕 -->
  <div id="bg-glow" style="position:absolute;top:50%;left:50%;width:900px;height:900px;transform:translate(-50%,-50%);background:radial-gradient(circle,{ACCENT_GLOW},transparent 70%);border-radius:50%;"></div>

  <!-- 装饰：四角坐标线 -->
  <div style="position:absolute;top:40px;left:40px;width:60px;height:1px;background:{ACCENT};opacity:0.4;"></div>
  <div style="position:absolute;top:40px;left:40px;width:1px;height:60px;background:{ACCENT};opacity:0.4;"></div>
  <div style="position:absolute;bottom:40px;right:40px;width:60px;height:1px;background:{ACCENT};opacity:0.4;"></div>
  <div style="position:absolute;bottom:40px;right:40px;width:1px;height:60px;background:{ACCENT};opacity:0.4;"></div>

  <!-- 核心数字 —— 画面中心 -->
  <div id="main-number" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:160px;font-weight:900;color:{ACCENT};font-family:'JetBrains Mono',monospace;text-shadow:0 0 60px {ACCENT_GLOW};z-index:10;">{DATA_VALUE}</div>

  <!-- 数字下方标签 -->
  <div id="main-label" style="position:absolute;top:calc(50% + 100px);left:50%;transform:translateX(-50%);font-size:28px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;letter-spacing:0.15em;z-index:10;">{DATA_LABEL}</div>

  <!-- 左上数据卡片 -->
  <div id="card-tl" class="card" style="position:absolute;top:120px;left:120px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:30px 40px;min-width:200px;z-index:5;">
    <div style="font-size:18px;color:#888;font-family:'Outfit','PingFang SC',sans-serif;">变化幅度</div>
    <div style="font-size:48px;font-weight:700;color:{ACCENT};font-family:'JetBrains Mono',monospace;margin-top:8px;">{DATA_CHANGE}</div>
  </div>

  <!-- 右上标签 -->
  <div id="card-tr" class="card" style="position:absolute;top:120px;right:120px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:24px 36px;z-index:5;">
    <div style="font-size:22px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;">{TAG1}</div>
  </div>

  <!-- 左下标签 -->
  <div id="card-bl" class="card" style="position:absolute;bottom:140px;left:120px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:24px 36px;z-index:5;">
    <div style="font-size:22px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;">{TAG2}</div>
  </div>

  <!-- 右下标题 -->
  <div id="headline" style="position:absolute;bottom:140px;right:120px;text-align:right;z-index:5;">
    <div style="font-size:36px;font-weight:700;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;line-height:1.3;">{HEADLINE}</div>
  </div>

</div>
<script>
var tl=gsap.timeline({{paused:true}});
tl.from("#bg-glow",{{scale:0.3,opacity:0,duration:2,ease:"sine.inOut"}},0);
tl.from("#main-number",{{scale:2.5,opacity:0,duration:0.7,ease:"back.out(1.7)"}},0.2);
tl.from("#main-label",{{opacity:0,y:20,duration:0.5,ease:"power3.out"}},0.6);
tl.from(".card",{{scale:0.8,opacity:0,y:30,duration:0.5,stagger:0.15,ease:"back.out(1.4)"}},0.4);
tl.from("#headline",{{opacity:0,x:30,duration:0.6,ease:"power3.out"}},0.7);
gsap.to("#main-number",{{textShadow:"0 0 40px {ACCENT_GLOW}",duration:1.5,repeat:-1,yoyo:true,ease:"sine.inOut"}});
window.__timelines=window.__timelines||{{}};
window.__timelines["{COMPOSITION_ID}"]=tl;
</script>
</body></html>'''


# ══════════════════════════════════════════════════════════
# 2. compare — 非对称对比：左大右小双栏
# ══════════════════════════════════════════════════════════
COMPARE = r'''<!DOCTYPE html>
<!-- vf-v5.6 -->
<html data-composition-id="{COMPOSITION_ID}" data-width="{W}" data-height="{H}" style="background:{BG};">
<head><meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:{BG};">
<div class="scene" style="position:relative;width:{W}px;height:{H}px;background:{BG};overflow:hidden;">

  <!-- 左侧大栏 —— 70% 宽度 -->
  <div id="left-col" style="position:absolute;top:100px;left:60px;width:55%;bottom:100px;border-right:1px solid rgba(255,255,255,0.1);padding-right:60px;display:flex;flex-direction:column;justify-content:center;z-index:5;">
    <div id="left-label" style="font-size:22px;color:{ACCENT};font-family:'Outfit','PingFang SC',sans-serif;letter-spacing:0.1em;margin-bottom:24px;">{TAG1}</div>
    <div id="left-title" style="font-size:56px;font-weight:800;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;line-height:1.2;">{HEADLINE}</div>
    <div id="left-desc" style="font-size:24px;color:#999;font-family:'Outfit','PingFang SC',sans-serif;line-height:1.6;margin-top:24px;">{SUBHEADLINE}</div>
  </div>

  <!-- 右侧小栏 —— 30% 宽度 -->
  <div id="right-col" style="position:absolute;top:100px;right:60px;width:30%;bottom:100px;display:flex;flex-direction:column;justify-content:center;align-items:center;z-index:5;">
    <div id="right-data" style="font-size:100px;font-weight:900;color:{ACCENT};font-family:'JetBrains Mono',monospace;text-shadow:0 0 40px {ACCENT_GLOW};">{DATA_VALUE}</div>
    <div id="right-label" style="font-size:24px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;margin-top:16px;text-align:center;">{DATA_LABEL}</div>
    <div id="right-change" style="font-size:36px;font-weight:700;color:{ACCENT};font-family:'JetBrains Mono',monospace;margin-top:24px;">{DATA_CHANGE}</div>
  </div>

  <!-- 中间分隔线 -->
  <div id="divider" style="position:absolute;top:100px;left:calc(55% + 60px);bottom:100px;width:1px;background:linear-gradient(180deg,transparent,{ACCENT},transparent);"></div>

</div>
<script>
var tl=gsap.timeline({{paused:true}});
tl.from("#left-col",{{x:-80,opacity:0,duration:0.7,ease:"power3.out"}},0);
tl.from("#right-col",{{x:80,opacity:0,duration:0.7,ease:"power3.out"}},0.2);
tl.from("#divider",{{scaleY:0,transformOrigin:"top",duration:1,ease:"power2.out"}},0.3);
gsap.to("#right-data",{{textShadow:"0 0 30px {ACCENT_GLOW}",duration:2,repeat:-1,yoyo:true,ease:"sine.inOut"}});
window.__timelines=window.__timelines||{{}};
window.__timelines["{COMPOSITION_ID}"]=tl;
</script>
</body></html>'''


# ══════════════════════════════════════════════════════════
# 3. flow — 横向流程：节点 + 连线
# ══════════════════════════════════════════════════════════
FLOW = r'''<!DOCTYPE html>
<!-- vf-v5.6 -->
<html data-composition-id="{COMPOSITION_ID}" data-width="{W}" data-height="{H}" style="background:{BG};">
<head><meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:{BG};">
<div class="scene" style="position:relative;width:{W}px;height:{H}px;background:{BG};overflow:hidden;">

  <div id="title" style="position:absolute;top:80px;left:100px;font-size:42px;font-weight:700;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;">{HEADLINE}</div>

  <!-- SVG 连线 -->
  <svg id="flow-svg" viewBox="0 0 1920 1080" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:1;" preserveAspectRatio="none">
    <line x1="260" y1="400" x2="460" y2="400" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="8 4" opacity="0.4"/>
    <line x1="720" y1="400" x2="920" y2="400" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="8 4" opacity="0.4"/>
    <line x1="1180" y1="400" x2="1380" y2="400" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="8 4" opacity="0.4"/>
  </svg>

  <!-- 节点 1 -->
  <div id="node1" class="node" style="position:absolute;top:310px;left:80px;width:180px;height:180px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.15);border-radius:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;z-index:5;">
    <div style="font-size:48px;font-weight:900;color:{ACCENT};font-family:'JetBrains Mono',monospace;">{DATA_VALUE}</div>
    <div style="font-size:18px;color:#aaa;font-family:'Outfit','PingFang SC',sans-serif;">{ITEM1}</div>
  </div>
  <!-- 节点 2 -->
  <div id="node2" class="node" style="position:absolute;top:310px;left:340px;width:180px;height:180px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.15);border-radius:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;z-index:5;">
    <div style="font-size:48px;font-weight:900;color:{ACCENT};font-family:'JetBrains Mono',monospace;">{ITEM2}</div>
    <div style="font-size:18px;color:#aaa;font-family:'Outfit','PingFang SC',sans-serif;">步骤 2</div>
  </div>
  <!-- 节点 3 -->
  <div id="node3" class="node" style="position:absolute;top:310px;left:600px;width:180px;height:180px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.15);border-radius:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;z-index:5;">
    <div style="font-size:48px;font-weight:900;color:{ACCENT};font-family:'JetBrains Mono',monospace;">{ITEM3}</div>
    <div style="font-size:18px;color:#aaa;font-family:'Outfit','PingFang SC',sans-serif;">步骤 3</div>
  </div>
  <!-- 节点 4 -->
  <div id="node4" class="node" style="position:absolute;top:310px;left:860px;width:180px;height:180px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.15);border-radius:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;z-index:5;">
    <div style="font-size:48px;font-weight:900;color:{ACCENT};font-family:'JetBrains Mono',monospace;">{ITEM4}</div>
    <div style="font-size:18px;color:#aaa;font-family:'Outfit','PingFang SC',sans-serif;">{TAG1}</div>
  </div>

  <!-- 底部说明 -->
  <div id="desc" style="position:absolute;bottom:140px;left:100px;right:100px;font-size:24px;color:#888;font-family:'Outfit','PingFang SC',sans-serif;line-height:1.5;text-align:center;">{SUBHEADLINE}</div>

</div>
<script>
var tl=gsap.timeline({{paused:true}});
tl.from("#title",{{opacity:0,y:-20,duration:0.5,ease:"power3.out"}},0);
tl.from("#flow-svg line",{{strokeDashoffset:30,duration:1.5,stagger:0.3,ease:"power2.inOut"}},0.3);
tl.from(".node",{{scale:0,opacity:0,duration:0.5,stagger:0.3,ease:"back.out(1.7)"}},0.4);
tl.from("#desc",{{opacity:0,y:20,duration:0.6,ease:"power3.out"}},1.0);
window.__timelines=window.__timelines||{{}};
window.__timelines["{COMPOSITION_ID}"]=tl;
</script>
</body></html>'''


# ══════════════════════════════════════════════════════════
# 4. hud — 全息面板：四角数据 + 中心主视觉
# ══════════════════════════════════════════════════════════
HUD = r'''<!DOCTYPE html>
<!-- vf-v5.6 -->
<html data-composition-id="{COMPOSITION_ID}" data-width="{W}" data-height="{H}" style="background:{BG};">
<head><meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:{BG};">
<div class="scene" style="position:relative;width:{W}px;height:{H}px;background:{BG};overflow:hidden;">

  <!-- HUD 网格背景 -->
  <div style="position:absolute;top:0;left:0;width:100%;height:100%;background-image:linear-gradient(rgba(255,255,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.03) 1px,transparent 1px);background-size:80px 80px;"></div>

  <!-- HUD 边框 -->
  <div style="position:absolute;top:40px;left:40px;right:40px;bottom:40px;border:1px solid rgba(255,255,255,0.08);border-radius:4px;pointer-events:none;"></div>

  <!-- 左上 KPI -->
  <div id="hud-tl" class="hud-card" style="position:absolute;top:60px;left:60px;width:220px;background:rgba(0,0,0,0.6);border:1px solid {ACCENT};border-radius:4px;padding:20px;z-index:5;">
    <div style="font-size:14px;color:{ACCENT};font-family:'Outfit','PingFang SC',sans-serif;letter-spacing:0.1em;">{DATA_LABEL}</div>
    <div style="font-size:48px;font-weight:900;color:#fff;font-family:'JetBrains Mono',monospace;margin-top:8px;">{DATA_VALUE}</div>
    <div style="font-size:16px;color:{ACCENT};font-family:'JetBrains Mono',monospace;margin-top:4px;">{DATA_CHANGE}</div>
  </div>

  <!-- 右上 KPI -->
  <div id="hud-tr" class="hud-card" style="position:absolute;top:60px;right:60px;width:220px;background:rgba(0,0,0,0.6);border:1px solid rgba(255,255,255,0.2);border-radius:4px;padding:20px;z-index:5;">
    <div style="font-size:14px;color:#888;font-family:'Outfit','PingFang SC',sans-serif;letter-spacing:0.1em;">{TAG1}</div>
    <div style="font-size:48px;font-weight:900;color:#fff;font-family:'JetBrains Mono',monospace;margin-top:8px;">{ITEM1}</div>
  </div>

  <!-- 中心标题 -->
  <div id="center-title" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;z-index:10;">
    <div style="font-size:72px;font-weight:900;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;text-shadow:0 0 40px {ACCENT_GLOW};">{HEADLINE}</div>
  </div>

  <!-- 左下信息 -->
  <div id="hud-bl" class="hud-card" style="position:absolute;bottom:60px;left:60px;width:220px;background:rgba(0,0,0,0.6);border:1px solid rgba(255,255,255,0.2);border-radius:4px;padding:20px;z-index:5;">
    <div style="font-size:14px;color:#888;font-family:'Outfit','PingFang SC',sans-serif;letter-spacing:0.1em;">{TAG2}</div>
    <div style="font-size:36px;font-weight:700;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;margin-top:8px;">{ITEM2}</div>
  </div>

  <!-- 右下信息 -->
  <div id="hud-br" class="hud-card" style="position:absolute;bottom:60px;right:60px;width:220px;background:rgba(0,0,0,0.6);border:1px solid rgba(255,255,255,0.2);border-radius:4px;padding:20px;z-index:5;">
    <div style="font-size:14px;color:#888;font-family:'Outfit','PingFang SC',sans-serif;letter-spacing:0.1em;">来源</div>
    <div style="font-size:18px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;margin-top:8px;">{ITEM3}</div>
  </div>

</div>
<script>
var tl=gsap.timeline({{paused:true}});
tl.from(".hud-card",{{scale:0.85,opacity:0,y:20,duration:0.5,stagger:0.2,ease:"back.out(1.4)"}},0.3);
tl.from("#center-title",{{scale:0.5,opacity:0,duration:0.8,ease:"power3.out"}},0.2);
gsap.to("#center-title",{{textShadow:"0 0 30px {ACCENT_GLOW}",duration:2,repeat:-1,yoyo:true,ease:"sine.inOut"}});
window.__timelines=window.__timelines||{{}};
window.__timelines["{COMPOSITION_ID}"]=tl;
</script>
</body></html>'''


# ══════════════════════════════════════════════════════════
# 5. list_alert — 红色警示列表
# ══════════════════════════════════════════════════════════
LIST_ALERT = r'''<!DOCTYPE html>
<!-- vf-v5.6 -->
<html data-composition-id="{COMPOSITION_ID}" data-width="{W}" data-height="{H}" style="background:{BG};">
<head><meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:{BG};">
<div class="scene" style="position:relative;width:{W}px;height:{H}px;background:{BG};overflow:hidden;">

  <!-- 顶部红色警示条 -->
  <div id="alert-bar" style="position:absolute;top:0;left:0;right:0;height:4px;background:{ACCENT};box-shadow:0 0 30px {ACCENT_GLOW};z-index:10;"></div>

  <!-- 标题 -->
  <div id="title" style="position:absolute;top:100px;left:100px;right:100px;">
    <div style="font-size:18px;color:{ACCENT};font-family:'Outfit','PingFang SC',sans-serif;letter-spacing:0.15em;margin-bottom:16px;">{TAG1}</div>
    <div style="font-size:64px;font-weight:800;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;line-height:1.2;">{HEADLINE}</div>
  </div>

  <!-- 列表项 -->
  <div id="items" style="position:absolute;top:340px;left:100px;right:100px;display:flex;flex-direction:column;gap:30px;z-index:5;">
    <div class="item" style="display:flex;align-items:center;gap:30px;">
      <div style="width:12px;height:12px;background:{ACCENT};border-radius:2px;box-shadow:0 0 10px {ACCENT_GLOW};flex-shrink:0;"></div>
      <div style="font-size:28px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;">{ITEM1}</div>
    </div>
    <div class="item" style="display:flex;align-items:center;gap:30px;">
      <div style="width:12px;height:12px;background:{ACCENT};border-radius:2px;box-shadow:0 0 10px {ACCENT_GLOW};flex-shrink:0;"></div>
      <div style="font-size:28px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;">{ITEM2}</div>
    </div>
    <div class="item" style="display:flex;align-items:center;gap:30px;">
      <div style="width:12px;height:12px;background:{ACCENT};border-radius:2px;box-shadow:0 0 10px {ACCENT_GLOW};flex-shrink:0;"></div>
      <div style="font-size:28px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;">{ITEM3}</div>
    </div>
    <div class="item" style="display:flex;align-items:center;gap:30px;">
      <div style="width:12px;height:12px;background:{ACCENT};border-radius:2px;box-shadow:0 0 10px {ACCENT_GLOW};flex-shrink:0;"></div>
      <div style="font-size:28px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;">{ITEM4}</div>
    </div>
  </div>

  <!-- 底部数据 -->
  <div id="bottom-data" style="position:absolute;bottom:100px;left:100px;font-size:56px;font-weight:900;color:{ACCENT};font-family:'JetBrains Mono',monospace;text-shadow:0 0 30px {ACCENT_GLOW};">{DATA_VALUE}</div>
  <div id="bottom-label" style="position:absolute;bottom:100px;left:calc(100px + 200px);font-size:24px;color:#999;font-family:'Outfit','PingFang SC',sans-serif;line-height:56px;">{DATA_LABEL}</div>

</div>
<script>
var tl=gsap.timeline({{paused:true}});
tl.from("#alert-bar",{{scaleX:0,duration:0.4,ease:"expo.out"}},0);
tl.from("#title",{{opacity:0,y:-30,duration:0.6,ease:"power3.out"}},0.2);
tl.from(".item",{{x:-100,opacity:0,duration:0.5,stagger:0.2,ease:"power3.out"}},0.4);
tl.from("#bottom-data",{{scale:1.5,opacity:0,duration:0.6,ease:"back.out(1.7)"}},1.0);
tl.from("#bottom-label",{{opacity:0,x:20,duration:0.5,ease:"power3.out"}},1.2);
window.__timelines=window.__timelines||{{}};
window.__timelines["{COMPOSITION_ID}"]=tl;
</script>
</body></html>'''


# ══════════════════════════════════════════════════════════
# 6. quote_hero — 压轴金句
# ══════════════════════════════════════════════════════════
QUOTE_HERO = r'''<!DOCTYPE html>
<!-- vf-v5.6 -->
<html data-composition-id="{COMPOSITION_ID}" data-width="{W}" data-height="{H}" style="background:{BG};">
<head><meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:{BG};">
<div class="scene" style="position:relative;width:{W}px;height:{H}px;background:{BG};overflow:hidden;">

  <!-- 径向光晕 -->
  <div id="glow" style="position:absolute;top:50%;left:50%;width:1200px;height:1200px;transform:translate(-50%,-50%);background:radial-gradient(circle,{ACCENT_GLOW},transparent 60%);border-radius:50%;z-index:0;"></div>

  <!-- 压轴文字 -->
  <div id="quote" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;z-index:10;">
    <div id="quote-text" style="font-size:100px;font-weight:900;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;line-height:1.3;text-shadow:0 0 60px {ACCENT_GLOW},0 0 120px {ACCENT_GLOW};">{QUOTE}</div>
  </div>

  <!-- 底部标签 -->
  <div id="tag" style="position:absolute;bottom:160px;left:50%;transform:translateX(-50%);font-size:24px;color:#666;font-family:'Outfit','PingFang SC',sans-serif;letter-spacing:0.2em;">{TAG1}</div>

</div>
<script>
var tl=gsap.timeline({{paused:true}});
tl.from("#glow",{{scale:0,opacity:0,duration:3,ease:"sine.inOut"}},0);
tl.from("#quote-text",{{opacity:0,filter:"blur(6px)",duration:1.5,ease:"power2.out"}},0.5);
tl.from("#tag",{{opacity:0,y:20,duration:1,ease:"power3.out"}},1.5);
gsap.to("#glow",{{scale:1.1,duration:4,repeat:-1,yoyo:true,ease:"sine.inOut"}});
window.__timelines=window.__timelines||{{}};
window.__timelines["{COMPOSITION_ID}"]=tl;
</script>
</body></html>'''


# ══════════════════════════════════════════════════════════
# 7. timeline_event — 时间线
# ══════════════════════════════════════════════════════════
TIMELINE = r'''<!DOCTYPE html>
<!-- vf-v5.6 -->
<html data-composition-id="{COMPOSITION_ID}" data-width="{W}" data-height="{H}" style="background:{BG};">
<head><meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:{BG};">
<div class="scene" style="position:relative;width:{W}px;height:{H}px;background:{BG};overflow:hidden;">

  <div id="title" style="position:absolute;top:80px;left:100px;font-size:42px;font-weight:700;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;">{HEADLINE}</div>

  <!-- 时间轴线 -->
  <div id="timeline" style="position:absolute;top:400px;left:100px;right:100px;height:2px;background:linear-gradient(90deg,{ACCENT},transparent);"></div>

  <!-- 时间点 1 -->
  <div id="t1" class="t-point" style="position:absolute;top:360px;left:180px;display:flex;flex-direction:column;align-items:center;">
    <div style="width:16px;height:16px;background:{ACCENT};border-radius:50%;box-shadow:0 0 20px {ACCENT_GLOW};"></div>
    <div style="font-size:18px;color:{ACCENT};font-family:'JetBrains Mono',monospace;margin-top:16px;">{ITEM1}</div>
    <div style="font-size:22px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;margin-top:8px;text-align:center;max-width:200px;">{TAG1}</div>
  </div>

  <!-- 时间点 2 -->
  <div id="t2" class="t-point" style="position:absolute;top:360px;left:580px;display:flex;flex-direction:column;align-items:center;">
    <div style="width:16px;height:16px;background:{ACCENT};border-radius:50%;box-shadow:0 0 20px {ACCENT_GLOW};"></div>
    <div style="font-size:18px;color:{ACCENT};font-family:'JetBrains Mono',monospace;margin-top:16px;">{ITEM2}</div>
    <div style="font-size:22px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;margin-top:8px;text-align:center;max-width:200px;">{TAG2}</div>
  </div>

  <!-- 时间点 3 -->
  <div id="t3" class="t-point" style="position:absolute;top:360px;left:980px;display:flex;flex-direction:column;align-items:center;">
    <div style="width:16px;height:16px;background:{ACCENT};border-radius:50%;box-shadow:0 0 20px {ACCENT_GLOW};"></div>
    <div style="font-size:18px;color:{ACCENT};font-family:'JetBrains Mono',monospace;margin-top:16px;">{ITEM3}</div>
    <div style="font-size:22px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;margin-top:8px;text-align:center;max-width:200px;">{ITEM4}</div>
  </div>

  <!-- 时间点 4 -->
  <div id="t4" class="t-point" style="position:absolute;top:360px;left:1380px;display:flex;flex-direction:column;align-items:center;">
    <div style="width:16px;height:16px;background:{ACCENT};border-radius:50%;box-shadow:0 0 20px {ACCENT_GLOW};"></div>
    <div style="font-size:18px;color:{ACCENT};font-family:'JetBrains Mono',monospace;margin-top:16px;">{ITEM5}</div>
    <div style="font-size:22px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;margin-top:8px;text-align:center;max-width:200px;">{DATA_LABEL}</div>
  </div>

  <!-- 底部注释 -->
  <div id="note" style="position:absolute;bottom:120px;left:100px;right:100px;font-size:20px;color:#666;font-family:'Outfit','PingFang SC',sans-serif;text-align:center;">{SUBHEADLINE}</div>

</div>
<script>
var tl=gsap.timeline({{paused:true}});
tl.from("#title",{{opacity:0,y:-20,duration:0.5,ease:"power3.out"}},0);
tl.from("#timeline",{{scaleX:0,transformOrigin:"left",duration:1.2,ease:"power2.out"}},0.3);
tl.from(".t-point",{{scale:0,opacity:0,duration:0.4,stagger:0.4,ease:"back.out(1.7)"}},0.5);
tl.from("#note",{{opacity:0,duration:0.8,ease:"power3.out"}},1.5);
window.__timelines=window.__timelines||{{}};
window.__timelines["{COMPOSITION_ID}"]=tl;
</script>
</body></html>'''


# ══════════════════════════════════════════════════════════
# 8. ranking_board — 排行榜
# ══════════════════════════════════════════════════════════
RANKING = r'''<!DOCTYPE html>
<!-- vf-v5.6 -->
<html data-composition-id="{COMPOSITION_ID}" data-width="{W}" data-height="{H}" style="background:{BG};">
<head><meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:{BG};">
<div class="scene" style="position:relative;width:{W}px;height:{H}px;background:{BG};overflow:hidden;">

  <div id="title" style="position:absolute;top:80px;left:100px;font-size:42px;font-weight:700;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;">{HEADLINE}</div>

  <!-- 排行 1 (冠军，高亮) -->
  <div id="r1" class="rank-item" style="position:absolute;top:200px;left:120px;right:120px;height:100px;background:linear-gradient(90deg,rgba(255,215,0,0.1),transparent);border-left:4px solid {ACCENT};display:flex;align-items:center;padding:0 30px;gap:30px;">
    <div style="font-size:48px;font-weight:900;color:{ACCENT};font-family:'JetBrains Mono',monospace;width:60px;">01</div>
    <div style="font-size:32px;font-weight:700;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;flex:1;">{ITEM1}</div>
    <div style="font-size:36px;font-weight:900;color:{ACCENT};font-family:'JetBrains Mono',monospace;">{DATA_VALUE}</div>
  </div>

  <!-- 排行 2 -->
  <div id="r2" class="rank-item" style="position:absolute;top:330px;left:120px;right:120px;height:90px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;align-items:center;padding:0 30px;gap:30px;">
    <div style="font-size:42px;font-weight:700;color:#999;font-family:'JetBrains Mono',monospace;width:60px;">02</div>
    <div style="font-size:28px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;flex:1;">{ITEM2}</div>
    <div style="font-size:32px;font-weight:700;color:#fff;font-family:'JetBrains Mono',monospace;">{ITEM3}</div>
  </div>

  <!-- 排行 3 -->
  <div id="r3" class="rank-item" style="position:absolute;top:450px;left:120px;right:120px;height:90px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;align-items:center;padding:0 30px;gap:30px;">
    <div style="font-size:42px;font-weight:700;color:#888;font-family:'JetBrains Mono',monospace;width:60px;">03</div>
    <div style="font-size:28px;color:#ccc;font-family:'Outfit','PingFang SC',sans-serif;flex:1;">{ITEM4}</div>
    <div style="font-size:32px;font-weight:700;color:#fff;font-family:'JetBrains Mono',monospace;">{ITEM5}</div>
  </div>

  <!-- 排行 4 -->
  <div id="r4" class="rank-item" style="position:absolute;top:570px;left:120px;right:120px;height:80px;display:flex;align-items:center;padding:0 30px;gap:30px;">
    <div style="font-size:36px;font-weight:600;color:#777;font-family:'JetBrains Mono',monospace;width:60px;">04</div>
    <div style="font-size:24px;color:#999;font-family:'Outfit','PingFang SC',sans-serif;flex:1;">{TAG1}</div>
    <div style="font-size:28px;color:#ccc;font-family:'JetBrains Mono',monospace;">{TAG2}</div>
  </div>

</div>
<script>
var tl=gsap.timeline({{paused:true}});
tl.from("#title",{{opacity:0,y:-20,duration:0.5,ease:"power3.out"}},0);
tl.from(".rank-item",{{x:-60,opacity:0,duration:0.5,stagger:0.15,ease:"power3.out"}},0.3);
gsap.to("#r1",{{boxShadow:"0 0 30px {ACCENT_GLOW}",duration:2,repeat:-1,yoyo:true,ease:"sine.inOut"}});
window.__timelines=window.__timelines||{{}};
window.__timelines["{COMPOSITION_ID}"]=tl;
</script>
</body></html>'''


# ══════════════════════════════════════════════════════════
# 9. opening — 开场（和 quote_hero 类似但更克制）
# ══════════════════════════════════════════════════════════
OPENING = r'''<!DOCTYPE html>
<!-- vf-v5.6 -->
<html data-composition-id="{COMPOSITION_ID}" data-width="{W}" data-height="{H}" style="background:{BG};">
<head><meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:{BG};">
<div class="scene" style="position:relative;width:{W}px;height:{H}px;background:{BG};overflow:hidden;">

  <!-- 微弱径向光晕 -->
  <div id="glow" style="position:absolute;top:50%;left:50%;width:1000px;height:1000px;transform:translate(-50%,-50%);background:radial-gradient(circle,{ACCENT_GLOW},transparent 70%);border-radius:50%;"></div>

  <!-- 话题关键词（模糊→清晰） -->
  <div id="title" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;z-index:10;">
    <div id="title-text" style="font-size:88px;font-weight:900;color:#fff;font-family:'Outfit','PingFang SC',sans-serif;line-height:1.3;">{HEADLINE}</div>
  </div>

  <!-- 底部副标题 -->
  <div id="sub" style="position:absolute;bottom:180px;left:50%;transform:translateX(-50%);font-size:30px;color:#777;font-family:'Outfit','PingFang SC',sans-serif;">{SUBHEADLINE}</div>

  <!-- 装饰：两侧细线 -->
  <div id="line-l" style="position:absolute;top:50%;left:120px;width:120px;height:1px;background:linear-gradient(90deg,transparent,{ACCENT});"></div>
  <div id="line-r" style="position:absolute;top:50%;right:120px;width:120px;height:1px;background:linear-gradient(270deg,transparent,{ACCENT});"></div>

</div>
<script>
var tl=gsap.timeline({{paused:true}});
tl.from("#glow",{{scale:0.5,opacity:0,duration:2.5,ease:"sine.inOut"}},0);
tl.from("#title-text",{{opacity:0,filter:"blur(8px)",duration:1.2,ease:"power2.out"}},0.5);
tl.from("#sub",{{opacity:0,y:20,duration:1,ease:"power3.out"}},1.2);
tl.from("#line-l",{{scaleX:0,transformOrigin:"right",duration:0.8,ease:"power2.out"}},0.5);
tl.from("#line-r",{{scaleX:0,transformOrigin:"left",duration:0.8,ease:"power2.out"}},0.5);
window.__timelines=window.__timelines||{{}};
window.__timelines["{COMPOSITION_ID}"]=tl;
</script>
</body></html>'''


# 模板映射表
TEMPLATES = {
    "data_impact": DATA_IMPACT,
    "compare": COMPARE,
    "flow": FLOW,
    "hud": HUD,
    "list_alert": LIST_ALERT,
    "quote_hero": QUOTE_HERO,
    "timeline_event": TIMELINE,
    "ranking_board": RANKING,
    "opening": OPENING,
    # 别名映射
    "dashboard": HUD,
    "data_dashboard": HUD,
    "code_terminal": HUD,
    "market_ticker": DATA_IMPACT,
}

# 默认模板（未知 visual_type 时使用）
FALLBACK = DATA_IMPACT
