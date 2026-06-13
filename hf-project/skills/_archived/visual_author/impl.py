"""
visual_author/skill.py — HTML创作（HyperFrames Step 4+5: Layout First + Animate）
功能：根据storyboard+design.md，生成HyperFrames可渲染的HTML composition
输出：index.html（包含所有场景的HTML+CSS+GSAP）

严格遵循HyperFrames规范：
1. Layout First: 先写静态HTML+CSS（终态），不加动画
2. Animate: 再加GSAP动画（gsap.from入场 + gsap.to出场）
3. 每个场景8-10个视觉元素
4. 标题64-120px，正文28-42px
5. 不使用exit动画（除最后场景）
6. 每个元素有具体动词（SLAMS/CASCADE/FLOATS/PULSES）
"""

import os
import json
import re
from pathlib import Path

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
HF_PROJECT_DIR = Path(__file__).parent.parent.parent
COMPOSITIONS_DIR = HF_PROJECT_DIR / "hf_render_project" / "compositions"
INDEX_HTML_PATH = HF_PROJECT_DIR / "hf_render_project" / "index.html"

# LLM配置
LLM_CONFIGS = [
    {
        "name": "deepseek",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    {
        "name": "mimo",
        "url": "https://token-plan-cn.xiaomimimo.com/v1/chat/completions",
        "model": "mimo-v2-pro",
        "env_key": "XIAOMI_API_KEY",
    },
]


def load_env():
    """加载环境变量"""
    from dotenv import load_dotenv
    possible_envs = [
        os.path.join(os.environ.get("HERMES_HOME", ""), ".env"),
        "E:/Hermes-Agent/.env",
        os.path.expanduser("~/.env"),
    ]
    for env_path in possible_envs:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            return


import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from llm_utils import call_llm as _shared_call_llm

def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 8000) -> str:
    """调用LLM via shared llm_utils（带中性化+fallback）"""
    return _shared_call_llm(prompt, system_prompt, max_tokens, timeout=300)


def extract_html_from_llm(response: str) -> str:
    """从LLM响应中提取HTML代码"""
    # 尝试提取```html...```代码块
    html_match = re.search(r'```html\s*(.*?)\s*```', response, re.DOTALL)
    if html_match:
        return html_match.group(1).strip()

    # 尝试提取<!DOCTYPE html>...</html>
    doctype_match = re.search(r'<!DOCTYPE html>.*?</html>', response, re.DOTALL | re.IGNORECASE)
    if doctype_match:
        return doctype_match.group(0).strip()

    # 尝试提取<html>...</html>
    html_tag_match = re.search(r'<html.*?</html>', response, re.DOTALL | re.IGNORECASE)
    if html_tag_match:
        return html_tag_match.group(0).strip()

    # 如果都没找到，返回整个响应（可能是纯HTML）
    return response.strip()


def generate_scene_html(scene_data: dict, design_md: str, scene_index: int, total_scenes: int) -> str:
    """为单个场景生成HTML"""

    scene_id = scene_data.get("scene_id", scene_index + 1)
    concept = scene_data.get("concept", "")
    mood = scene_data.get("mood", "")
    visual_type = scene_data.get("visual_type", "quote_hero")
    choreography = scene_data.get("choreography", {})
    depth_layers = scene_data.get("depth_layers", {})
    density_target = scene_data.get("density_target", 8)
    key_elements = scene_data.get("key_elements", [])
    voiceover = scene_data.get("voiceover_text", "")
    timestamp = scene_data.get("timestamp", {})
    transition_in = scene_data.get("transition_in", "velocity_upward")
    transition_out = scene_data.get("transition_out", "velocity_upward")

    # 构建system prompt
    system_prompt = f"""你是一个专业的视频视觉设计师，正在为HyperFrames生成HTML composition。

你的任务是为一个场景生成完整的HTML+CSS+GSAP代码。

## 严格规则（Non-Negotiable）

### Layout First（先布局后动画）
1. 先写静态HTML+CSS（终态），不加动画
2. CSS位置是ground truth
3. 然后用gsap.from()添加入场动画
4. 最后场景才允许gsap.to()退出动画

### 尺寸要求（Video Scale，不是Web Scale）
- 标题: 64-120px，占屏幕宽度60-80%
- 副标题: 36-48px
- 正文: 28-36px
- 数据: 48-80px，font-variant-numeric: tabular-nums
- 标签: 18-24px
- 装饰透明度: 12-25%（低于10%看不见）
- 边框: 2-4px
- Padding: 80-120px

### 密度要求
- 每个场景8-10个视觉元素
- 必须有背景层（纹理/渐变/光晕）
- 必须有前景层（装饰元素）
- 空场景 = 失败

### GSAP规则
- 所有timeline从{{ paused: true }}开始
- 注册到window.__timelines["scene-{scene_id}"]
- 用gsap.from()入场，不要gsap.to()退出（除最后场景）
- 第一个动画偏移0.1-0.3s（不要t=0）
- 每个场景至少3种不同的ease
- 不要repeat: -1
- 不要Math.random()
- 不要async/await

### CSS规则
- .scene-content必须用width:100%; height:100%; padding:Npx; display:flex; flex-direction:column;
- 不要用position:absolute定位内容容器（只用于装饰）
- 不要用非ASCII字符在CSS注释中

### 元素ID
- 每个元素必须有唯一ID：s{scene_id}-elementname
- 例如：s1-title, s1-subtitle, s1-card, s1-glow

### 输出格式
只输出一个完整的HTML文件，包含：
- <!DOCTYPE html>
- <html> with data-composition-id, data-width, data-height
- <style> with all CSS
- <script> with GSAP CDN + timeline
- 不要<template>标签（这是主composition）

### 动画动词参考
- high_impact: SLAMS, CRASHES, PUNCHES, STAMPS
- medium_energy: CASCADE, SLIDES, DROPS, FILLS
- low_energy: FLOATS, MORPHS, COUNTS UP, FADES IN
- ambient: PULSES, BREATHES, GLOWS, SHIMMERS
"""

    # 构建prompt
    prompt = f"""## 场景信息

Scene ID: {scene_id}
Visual Type: {visual_type}
Concept: {concept}
Mood: {mood}
Density Target: {density_target} elements
Timestamp: {timestamp.get('start', 0):.1f}s - {timestamp.get('end', 10):.1f}s (duration: {timestamp.get('end', 10) - timestamp.get('start', 0):.1f}s)
Is Last Scene: {scene_index == total_scenes - 1}

## Choreography（动画动词）
{json.dumps(choreography, ensure_ascii=False, indent=2)}

## Depth Layers（层次）
{json.dumps(depth_layers, ensure_ascii=False, indent=2)}

## Key Elements（关键元素）
{json.dumps(key_elements, ensure_ascii=False, indent=2)}

## 配音文案
{voiceover}

## Design System（设计约束）
{design_md[:3000]}

## Transition
- 入场: {transition_in}
- 出场: {transition_out}

请生成完整的HTML文件。确保：
1. 8-10个视觉元素
2. 标题64-120px
3. 每个元素有唯一ID
4. GSAP timeline注册到window.__timelines
5. 使用design system中的颜色和字体
"""

    # 调用LLM
    llm_response = call_llm(prompt, system_prompt, max_tokens=8000)

    if not llm_response:
        print(f"  ❌ [visual-author] 场景{scene_id} LLM返回为空，使用fallback")
        return generate_fallback_scene(scene_data, design_md)

    # 提取HTML
    html = extract_html_from_llm(llm_response)

    # 验证基本结构
    if "<html" not in html.lower() or "</html>" not in html.lower():
        print(f"  ⚠️ [visual-author] 场景{scene_id} HTML结构不完整，使用fallback")
        return generate_fallback_scene(scene_data, design_md)

    # 修复GSAP注册：确保注册到window.__timelines
    if "window.__timelines" not in html:
        # 添加注册代码
        html = html.replace(
            "</script>",
            f'\n    window.__timelines = window.__timelines || {{}};\n    window.__timelines["scene-{scene_id}"] = tl;\n</script>'
        )

    # 修复：移除.play()调用（HyperFrames控制播放）
    html = re.sub(r'\.play\(\)\s*;', ';', html)

    return html


def generate_fallback_scene(scene_data: dict, design_md: str) -> str:
    """生成fallback场景HTML（当LLM失败时）"""

    scene_id = scene_data.get("scene_id", 1)
    voiceover = scene_data.get("voiceover_text", "")
    visual_type = scene_data.get("visual_type", "quote_hero")
    timestamp = scene_data.get("timestamp", {})
    duration = timestamp.get("end", 10) - timestamp.get("start", 0)

    # 从design.md提取颜色
    bg_color = "#0a0a0a"
    primary_color = "#00D4FF"
    accent_color = "#FF4081"
    data_color = "#FFD700"

    color_match = re.search(r'背景.*?#([0-9a-fA-F]{6})', design_md)
    if color_match:
        bg_color = f"#{color_match.group(1)}"
    color_match = re.search(r'主色.*?#([0-9a-fA-F]{6})', design_md)
    if color_match:
        primary_color = f"#{color_match.group(1)}"
    color_match = re.search(r'强调色.*?#([0-9a-fA-F]{6})', design_md)
    if color_match:
        accent_color = f"#{color_match.group(1)}"

    # 截取配音文案的前50个字符作为标题
    title_text = voiceover[:50].replace('"', '&quot;').replace("'", "&#39;") if voiceover else f"Scene {scene_id}"
    subtitle_text = voiceover[50:100].replace('"', '&quot;').replace("'", "&#39;") if len(voiceover) > 50 else ""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  [data-composition-id="scene-{scene_id}"] {{
    width: 1920px;
    height: 1080px;
    background: {bg_color};
    font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    color: #FFFFFF;
    overflow: hidden;
    position: relative;
  }}
  .scene-content {{
    width: 100%;
    height: 100%;
    padding: 100px 120px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 32px;
    position: relative;
    z-index: 2;
  }}
  .title {{
    font-size: 80px;
    font-weight: bold;
    line-height: 1.2;
    max-width: 80%;
  }}
  .subtitle {{
    font-size: 36px;
    font-weight: 400;
    opacity: 0.8;
    max-width: 70%;
  }}
  .glow {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, {primary_color}33 0%, transparent 70%);
    border-radius: 50%;
    z-index: 1;
  }}
  .accent-line {{
    position: absolute;
    bottom: 80px;
    right: 120px;
    width: 200px;
    height: 4px;
    background: {accent_color};
    z-index: 3;
  }}
  .grid-bg {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image:
      linear-gradient({primary_color}11 1px, transparent 1px),
      linear-gradient(90deg, {primary_color}11 1px, transparent 1px);
    background-size: 60px 60px;
    z-index: 0;
  }}
  .badge {{
    display: inline-block;
    padding: 8px 24px;
    border: 2px solid {primary_color};
    border-radius: 8px;
    font-size: 24px;
    color: {primary_color};
    text-transform: uppercase;
    letter-spacing: 2px;
  }}
  .data-number {{
    font-size: 72px;
    font-weight: bold;
    color: {data_color};
    font-variant-numeric: tabular-nums;
  }}
  .ghost-text {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 200px;
    font-weight: 900;
    color: {primary_color}08;
    white-space: nowrap;
    z-index: 0;
  }}
  .grain {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0.03;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    z-index: 1;
  }}
</style>
</head>
<body>
  <div data-composition-id="scene-{scene_id}" data-width="1920" data-height="1080">
    <div class="grid-bg"></div>
    <div class="grain"></div>
    <div class="ghost-text">SCENE {scene_id}</div>
    <div class="glow"></div>
    <div class="scene-content">
      <div class="badge">Scene {scene_id}</div>
      <div class="title" id="s{scene_id}-title">{title_text}</div>
      {"<div class='subtitle' id='s{scene_id}-subtitle'>" + subtitle_text + "</div>" if subtitle_text else ""}
    </div>
    <div class="accent-line" id="s{scene_id}-accent"></div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});

    // Entrance animations
    tl.from("#s{scene_id}-title", {{
      y: 60, opacity: 0, duration: 0.7, ease: "power3.out"
    }}, 0.2);
    tl.from("#s{scene_id}-subtitle", {{
      y: 40, opacity: 0, duration: 0.5, ease: "power2.out"
    }}, 0.4);
    tl.from("#s{scene_id}-accent", {{
      scaleX: 0, opacity: 0, duration: 0.6, ease: "expo.out", transformOrigin: "left center"
    }}, 0.3);

    // Ambient animations
    tl.to(".glow", {{
      scale: 1.1, opacity: 0.8, duration: 3, ease: "sine.inOut", yoyo: true, repeat: 3
    }}, 0);

    window.__timelines["scene-{scene_id}"] = tl;
  </script>
</body>
</html>"""

    return html


def generate_main_index(scenes_html: list, voice_path: str = "", bgm_path: str = "", total_duration: float = 0) -> str:
    """生成主index.html，引用所有场景"""

    # 计算总时长
    if not total_duration:
        total_duration = len(scenes_html) * 10  # 默认每场景10秒

    # 生成场景引用
    scene_refs = ""
    for i, _ in enumerate(scenes_html):
        scene_id = i + 1
        start_time = i * (total_duration / len(scenes_html))
        duration = total_duration / len(scenes_html)
        scene_refs += f"""
    <div id="el-{scene_id}"
         data-composition-id="scene-{scene_id}"
         data-composition-src="compositions/beat-{scene_id:02d}.html"
         data-start="{start_time:.1f}"
         data-duration="{duration:.1f}"
         data-track-index="{scene_id}">
    </div>"""

    # 音频引用
    audio_refs = ""
    if voice_path:
        audio_refs += f"""
    <audio id="voice"
           data-start="0"
           data-duration="{total_duration:.1f}"
           data-track-index="100"
           src="{voice_path}"
           data-volume="1.0">
    </audio>"""
    if bgm_path:
        audio_refs += f"""
    <audio id="bgm"
           data-start="0"
           data-duration="{total_duration:.1f}"
           data-track-index="101"
           src="{bgm_path}"
           data-volume="0.3">
    </audio>"""

    index_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #000; }}
</style>
</head>
<body>
  <div data-composition-id="root"
       data-width="1920"
       data-height="1080"
       data-start="0"
       data-duration="{total_duration:.1f}">
{scene_refs}
{audio_refs}
  </div>

  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    window.__timelines = window.__timelines || {{}};
    // Sub-composition timelines are loaded automatically
  </script>
</body>
</html>"""

    return index_html


def run(context: dict) -> dict:
    """主入口：生成HTML composition"""

    topic = context.get("topic", "未知话题")
    print(f"  [visual-author] 为 '{topic}' 生成HTML composition...")

    # 加载环境变量
    load_env()

    # 读取storyboard
    storyboard_path = context.get("storyboard_path") or str(OUTPUT_DIR / "storyboard.json")
    if not os.path.exists(storyboard_path):
        print(f"  ❌ [visual-author] 找不到storyboard: {storyboard_path}")
        return context

    with open(storyboard_path, "r", encoding="utf-8") as f:
        storyboard = json.load(f)

    # 读取design.md
    design_md_path = context.get("design_md_path") or str(OUTPUT_DIR / "design.md")
    design_md = ""
    if os.path.exists(design_md_path):
        with open(design_md_path, "r", encoding="utf-8") as f:
            design_md = f.read()

    # 音频路径
    voice_path = context.get("voice_path") or str(OUTPUT_DIR / "step05_voice.wav")
    bgm_path = context.get("bgm_path") or str(OUTPUT_DIR / "step07_bgm.wav")
    if not os.path.exists(voice_path):
        voice_path = ""
    if not os.path.exists(bgm_path):
        bgm_path = ""

    # 计算总时长
    total_duration = 0
    for scene in storyboard:
        ts = scene.get("timestamp", {})
        end = ts.get("end", 0)
        if end > total_duration:
            total_duration = end
    if not total_duration:
        total_duration = len(storyboard) * 10

    # 创建目录
    COMPOSITIONS_DIR.mkdir(parents=True, exist_ok=True)

    # 为每个场景生成HTML
    scenes_html = []
    for i, scene_data in enumerate(storyboard):
        scene_id = scene_data.get("scene_id", i + 1)
        print(f"  [visual-author] 生成场景 {scene_id}/{len(storyboard)}...")

        html = generate_scene_html(scene_data, design_md, i, len(storyboard))
        scenes_html.append(html)

        # 保存场景HTML
        COMPOSITIONS_DIR.mkdir(parents=True, exist_ok=True)
        scene_path = COMPOSITIONS_DIR / f"beat-{scene_id:02d}.html"
        scene_path.write_text(html, encoding="utf-8")
        print(f"  [visual-author] 场景{scene_id} 已保存: {scene_path}")

    # 生成主index.html
    index_html = generate_main_index(scenes_html, voice_path, bgm_path, total_duration)
    INDEX_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_HTML_PATH.write_text(index_html, encoding="utf-8")
    print(f"  [visual-author] 主index.html已保存: {INDEX_HTML_PATH}")

    # 更新context
    context["index_html_path"] = str(INDEX_HTML_PATH)
    context["compositions_dir"] = str(COMPOSITIONS_DIR)
    context["total_duration"] = total_duration
    context["scene_count"] = len(storyboard)

    return context


if __name__ == "__main__":
    # 测试
    test_context = {
        "topic": "2026高考第一批显眼包出现了",
        "storyboard_path": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/output/storyboard.json",
        "design_md_path": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/output/design.md",
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  场景数: {result.get('scene_count')}")
    print(f"  总时长: {result.get('total_duration'):.1f}s")
    print(f"  输出: {result.get('index_html_path')}")
