"""
storyboard/skill.py — 分镜设计（HyperFrames Step 2+3: Prompt Expansion + Plan）
功能：根据脚本+设计系统+时间戳，生成每个场景的创意方向
输出：storyboard.json（concept/mood/choreography/transition/depth-layers）

这是visual-author的输入，决定了视频的视觉质量。
"""

import os
import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from llm_utils import call_llm, call_llm_batch

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
STORYBOARD_PATH = OUTPUT_DIR / "storyboard.json"

# LLM配置已移至llm_utils.py

# 视觉类型定义
VISUAL_TYPES = {
    "data_impact": {
        "description": "数据冲击——大数字+进度条+趋势箭头",
        "use_when": "场景有具体数字、百分比、统计数据",
        "elements": ["big_number", "progress_bar", "trend_arrow", "data_label", "comparison_card"],
    },
    "dashboard": {
        "description": "仪表盘——多指标并列展示",
        "use_when": "场景有多个数据指标需要并列展示",
        "elements": ["metric_card", "chart_placeholder", "status_indicator", "grid_layout"],
    },
    "compare": {
        "description": "对比——A vs B的数据对比",
        "use_when": "场景有明确的两方对比（N个人...M个、A比B多X%）",
        "elements": ["vs_divider", "left_panel", "right_panel", "comparison_bar", "highlight_winner"],
    },
    "flow": {
        "description": "流程——步骤/时间线/因果链",
        "use_when": "场景描述流程、步骤、时间线",
        "elements": ["step_card", "arrow_connector", "timeline_dot", "progress_indicator"],
    },
    "list_alert": {
        "description": "清单警告——条目+强调",
        "use_when": "场景列举多个要点、警告、注意事项",
        "elements": ["list_item", "alert_badge", "check_mark", "warning_icon"],
    },
    "hud": {
        "description": "HUD信息——科技感数据叠加",
        "use_when": "场景需要科技感、未来感的信息展示",
        "elements": ["hud_frame", "data_readout", "scan_line", "target_marker"],
    },
    "quote_hero": {
        "description": "金句主角——大字+背景氛围",
        "use_when": "场景是情感升华、金句、总结、CTA",
        "elements": ["hero_text", "atmosphere_glow", "accent_line", "ghost_text"],
    },
    "code_terminal": {
        "description": "终端/代码——深色终端+代码雨+命令行风格",
        "use_when": "场景涉及技术、开源项目、代码、GitHub",
        "elements": ["terminal_window", "code_block", "cursor_blink", "file_tree", "commit_log"],
    },
    "ranking_board": {
        "description": "排行榜——排名列表+动态高亮",
        "use_when": "场景涉及排名、Top N、对比多个项目",
        "elements": ["rank_number", "project_card", "score_bar", "crown_icon", "trend_arrow"],
    },
    "product_showcase": {
        "description": "产品展示——模拟产品页面/应用界面",
        "use_when": "场景介绍具体产品、工具、应用（如enableMacosAI风格）",
        "elements": ["app_mockup", "feature_grid", "screenshot_frame", "download_cta", "rating_stars"],
    },
    "timeline_event": {
        "description": "时间轴——事件节点+因果连线",
        "use_when": "场景描述事件发展、历史进程、阶段变化",
        "elements": ["timeline_line", "event_node", "date_label", "connector_arrow", "milestone_marker"],
    },
    "market_ticker": {
        "description": "行情播报——K线+涨跌幅+滚动数据",
        "use_when": "场景涉及股票、投资、市场数据、涨跌",
        "elements": ["price_display", "change_percent", "mini_chart", "volume_bar", "market_index"],
    },
}

# 动画动词库
CHOREOGRAPHY_VERBS = {
    "high_impact": ["SLAMS", "CRASHES", "PUNCHES", "STAMPS", "SHATTERS", "BURSTS"],
    "medium_energy": ["CASCADE", "SLIDES", "DROPS", "FILLS", "DRAWS", "SWEEPS"],
    "low_energy": ["FLOATS", "MORPHS", "COUNTS UP", "FADES IN", "TYPES ON", "DRIFTS"],
    "ambient": ["PULSES", "BREATHES", "GLOWS", "SHIMMERS", "ORBITS", "ROTATES"],
}

# 转场类型
TRANSITIONS = {
    "velocity_upward": "exit y:-150 blur:30px 0.33s power2.in → entry y:150→0 blur:0 1.0s power2.out",
    "whip_pan": "exit x:-400 blur:24px 0.3s power3.in → entry x:400→0 blur:0 0.3s power3.out",
    "blur_through": "exit blur:20px 0.3s → entry blur:0 0.25s power3.out",
    "zoom_through": "exit scale:1→1.2 blur:20px 0.2s power3.in → entry scale:0.75→1 blur:0 0.5s expo.out",
    "hard_cut": "直接切换，无过渡",
    "shader_cross_warp": "Cross-Warp Morph 0.5-0.8s power2.inOut",
    "shader_cinematic_zoom": "Cinematic Zoom 0.4-0.6s power2.inOut",
}





def detect_visual_type(text: str, has_data: bool = False) -> str:
    """根据文本内容自动检测visual_type"""
    text_lower = text.lower()

    # 数据场景
    if has_data or any(kw in text for kw in ["%", "数据", "统计", "比例", "增长", "下降", "倍", "万", "亿"]):
        # 对比场景
        if any(kw in text for kw in ["vs", "对比", "比", "而", "但是", "却"]):
            return "compare"
        return "data_impact"

    # 流程场景
    if any(kw in text for kw in ["首先", "然后", "最后", "步骤", "流程", "阶段", "过程"]):
        return "flow"

    # 清单场景
    if any(kw in text for kw in ["第一", "第二", "第三", "一是", "二是", "三是", "包括"]):
        return "list_alert"

    # 金句场景
    if any(kw in text for kw in ["说白了", "归根结底", "本质上", "你品", "细品", "真相"]):
        return "quote_hero"

    # 技术/开源场景
    if any(kw in text for kw in ["GitHub", "开源", "代码", "Star", "项目", "仓库", "终端", "CLI"]):
        if any(kw in text for kw in ["排名", "Top", "第一", "最火", "热门"]):
            return "ranking_board"
        if any(kw in text for kw in ["工具", "应用", "软件", "平台", "产品"]):
            return "product_showcase"
        return "code_terminal"

    # 投资/市场场景
    if any(kw in text for kw in ["股", "涨", "跌", "市场", "投资", "基金", "IPO", "估值", "市值"]):
        return "market_ticker"

    # 时间线场景
    if any(kw in text for kw in ["时间", "发展", "历程", "阶段", "从...到", "演变"]):
        return "timeline_event"

    # 默认：quote_hero（最通用）
    return "quote_hero"


def match_timestamps(sections: list, transcript_segments: list) -> list:
    """将transcript的时间戳映射到script的段落
    
    transcript有48个片段，script有9个段落。
    需要把transcript的片段按script的段落合并。
    """
    if not transcript_segments:
        return []
    
    # 计算每个段落的大致字符数
    total_chars = sum(len(s.get("content", "") or s.get("voiceover", "")) for s in sections)
    if total_chars == 0:
        return []
    
    timestamps = []
    seg_idx = 0
    
    for section in sections:
        text = section.get("content", "") or section.get("voiceover", "")
        section_chars = len(text)
        
        # 计算这个段落应该占多少时间
        section_ratio = section_chars / total_chars
        total_duration = transcript_segments[-1].get("end", 0) if transcript_segments else 0
        estimated_duration = total_duration * section_ratio
        
        # 找到对应的transcript片段
        start_time = transcript_segments[seg_idx].get("start", 0) if seg_idx < len(transcript_segments) else 0
        
        # 累积字符数，找到这个段落结束的位置
        accumulated_chars = 0
        while seg_idx < len(transcript_segments):
            seg_text = transcript_segments[seg_idx].get("text", "")
            accumulated_chars += len(seg_text)
            if accumulated_chars >= section_chars * 0.8:  # 允许20%误差
                break
            seg_idx += 1
        
        end_time = transcript_segments[min(seg_idx, len(transcript_segments)-1)].get("end", 0)
        seg_idx = min(seg_idx + 1, len(transcript_segments) - 1)
        
        timestamps.append({
            "start": round(start_time, 1),
            "end": round(end_time, 1),
        })
    
    return timestamps

def generate_storyboard(script_data: dict, design_md: str, transcript_data: dict = None, total_duration: float = 0) -> list:
    """生成storyboard（根据口播内容决定视觉设计）"""

    # 读取口播段落（兼容新旧格式）
    sections = script_data.get("voiceover_sections", [])
    if not sections:
        # 兼容旧格式：scenes
        sections = script_data.get("scenes", [])
    
    topic = script_data.get("topic", "")

    # 动态场景数：根据配音总时长计算目标场景数
    num_sections = len(sections)
    if total_duration > 0:
        target_scenes = max(5, min(15, round(total_duration / 12)))  # 每场景约12秒
    else:
        target_scenes = num_sections
    
    scene_guidance = ""
    if target_scenes > num_sections:
        scene_guidance = f"\n\n⚠️ 重要：配音总时长{total_duration:.0f}秒，需要{target_scenes}个场景，但只有{num_sections}个段落。请将较长的段落拆分为2个子场景，每个子场景有独立的视觉概念。输出{target_scenes}个场景。"
    elif target_scenes < num_sections:
        scene_guidance = f"\n\n⚠️ 重要：配音总时长{total_duration:.0f}秒，目标{target_scenes}个场景。请合并相邻的短段落。输出{target_scenes}个场景。"
    else:
        scene_guidance = f"\n\n配音总时长{total_duration:.0f}秒，共{num_sections}个段落，每段一个场景。"

    # 构建system prompt
    system_prompt = """你是一个专业的视频导演兼视觉设计师。你的任务是根据口播内容，为每个段落设计视觉方案。

你需要为每个段落输出以下信息：
1. **concept** (string): 这个场景的创意概念，2-3句话描述观众的体验
2. **mood** (string): 情绪方向，用文化/设计参考描述（不是hex值）
3. **visual_type** (string): 视觉类型，从以下选择：
   - data_impact: 数据冲击（大数字+进度条+趋势箭头）
   - dashboard: 仪表盘（多指标并列展示）
   - compare: 对比（A vs B的数据对比）
   - flow: 流程（步骤/时间线/因果链）
   - list_alert: 清单警告（条目+强调）
   - hud: HUD信息（科技感数据叠加）
   - quote_hero: 金句主角（大字+背景氛围）
   - code_terminal: 终端/代码风（深色终端+代码雨）
   - ranking_board: 排行榜（排名列表+动态高亮）
   - product_showcase: 产品展示（模拟应用界面）
   - timeline_event: 时间轴（事件节点+因果连线）
   - market_ticker: 行情播报（K线+涨跌幅+滚动数据）
4. **choreography** (object): 每个元素的动画动词
   - 标题用high_impact动词（SLAMS/CRASHES/PUNCHES）
   - 副标题用medium_energy动词（CASCADE/SLIDES/DROPS）
   - 数据用low_energy动词（COUNTS UP/FLOATS/MORPHS）
   - 装饰用ambient动词（PULSES/BREATHES/GLOWS）
5. **transition_in** (string): 入场转场类型
6. **transition_out** (string): 出场转场类型
7. **depth_layers** (object): 前景/中景/背景层次
8. **density_target** (number): 目标元素数量（8-10）
9. **key_elements** (array): 这个场景的关键视觉元素列表，每个元素用结构化格式：
   - 数据型: {"type": "data", "label": "指标名", "value": "数值", "unit": "单位", "trend": "up/down/flat"}
   - 标签型: {"type": "tag", "text": "标签文字"}
   - 标题型: {"type": "title", "text": "标题文字"}
   - 列表型: {"type": "list", "items": ["条目1", "条目2", ...]}
   - 对比型: {"type": "compare", "left": {"label":"A","value":"x"}, "right": {"label":"B","value":"y"}}

输出JSON数组，每个元素对应一个段落的视觉方案。只输出JSON，不要其他内容。"""

    # 匹配时间戳（仅在没有voice_scene_durations时使用估算）
    matched_timestamps = []
    # voice_scene_durations由voice_gen提供精确时长，优先使用
    # 这里的估算只作为fallback
    
    # 构建prompt
    sections_text = ""
    for i, section in enumerate(sections):
        # 新格式用content和talking_point，旧格式用voiceover和visual_hint
        content = section.get("content", "") or section.get("voiceover", "")
        talking_point = section.get("talking_point", "") or section.get("visual_hint", "")
        sections_text += f"""
段落{i+1}:
  口播内容: {content}
  核心主题: {talking_point}
"""

    # 添加时间戳信息
    timing_text = ""
    if transcript_data:
        timing_text = "\n\n时间戳信息（从WhisperX转录）:\n"
        for i, seg in enumerate(transcript_data.get("segments", [])):
            timing_text += f"  段落{i+1}: {seg.get('start', 0):.1f}s - {seg.get('end', 0):.1f}s\n"

    # 限制prompt长度，避免超时
    design_summary = design_md[:1500] if len(design_md) > 1500 else design_md
    
    sections_summary = ""
    for i, section in enumerate(sections):
        sec_content = section.get("content", "") or section.get("voiceover", "")
        talking_point = section.get("talking_point", "") or section.get("visual_hint", "")
        sections_summary += "\n段落" + str(i+1) + ": " + sec_content[:60] + "..."
        if talking_point:
            sections_summary += "\n  主题: " + talking_point[:50]

    timing_summary = ""
    if matched_timestamps:
        timing_summary = "\n\n时间戳:"
        for i, ts in enumerate(matched_timestamps):
            timing_summary += "\n  段落" + str(i+1) + ": " + str(round(ts.get("start", 0), 1)) + "s - " + str(round(ts.get("end", 0), 1)) + "s"

    prompt = "Topic: " + topic + "\n\n设计系统:\n" + design_summary + "\n\n口播段落:\n" + sections_summary + timing_summary + scene_guidance + "\n\n请为每个段落设计视觉方案。输出JSON数组，每个元素包含：scene_id, visual_type, concept, key_elements。"

    # 调用LLM
    llm_response = call_llm(prompt, system_prompt, max_tokens=8000)

    # 解析响应
    storyboard = []
    if llm_response:
        try:
            # 先去除markdown代码块
            cleaned = re.sub(r'```json\s*', '', llm_response)
            cleaned = re.sub(r'```\s*$', '', cleaned).strip()
            # 提取JSON数组
            json_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
            if json_match:
                storyboard = json.loads(json_match.group())
                print(f"  ✅ [storyboard] LLM解析成功: {len(storyboard)} 个视觉方案")
        except json.JSONDecodeError:
            print("  ⚠️ [storyboard] LLM返回的JSON解析失败")

    # 如果LLM失败，用fallback生成（根据口播内容差异化）
    if not storyboard:
        print("  ⚠️ [storyboard] 使用fallback生成...")
        storyboard = []
        # 视觉类型轮换，避免重复
        type_cycle = ["data_impact", "quote_hero", "dashboard", "compare", "hud", "flow", "list_alert", "quote_hero"]
        # 动画动词轮换
        title_verbs = ["SLAMS", "CRASHES", "BURSTS", "PUNCHES", "STAMPS", "SHATTERS"]
        content_verbs = ["FLOATS", "MORPHS", "COUNTS UP", "FADES IN", "DRIFTS", "TYPES ON"]
        # depth_layers 变体
        depth_variants = [
            {"bg": "dark fill + radial glow", "mg": "content cards", "fg": "accent lines + grain"},
            {"bg": "gradient mesh + particles", "mg": "floating panels", "fg": "scan lines + noise"},
            {"bg": "circuit pattern + pulse", "mg": "data cards stack", "fg": "glow edges + dust"},
            {"bg": "grid wireframe + nebula", "mg": "metric panels", "fg": "laser lines + sparks"},
            {"bg": "matrix rain + void", "mg": "glass cards", "fg": "hologram flicker"},
            {"bg": "hex grid + aurora", "mg": "info blocks", "fg": "particle stream"},
            {"bg": "dot matrix + glow orbs", "mg": "stacked modules", "fg": "energy ribbons"},
            {"bg": "noise texture + gradient", "mg": "quote panel", "fg": "accent strokes"},
        ]

        for i, section in enumerate(sections):
            content = section.get("content", "") or section.get("voiceover", "")
            talking_point = section.get("talking_point", "") or section.get("visual_hint", "")

            # 从口播内容中提取关键元素
            key_elems = ["title"]
            # 提取数字/数据
            data_matches = re.findall(r'[\d,.]+[万亿%倍零一二三四五六七八九十百千万]+', content)
            if data_matches:
                key_elems.extend([f"data:{d}" for d in data_matches[:2]])
                key_elems.append("progress_bar")
            # 提取关键名词短语
            nouns = re.findall(r'[\u4e00-\u9fff]{2,6}', content)
            seen = set()
            for n in nouns:
                if n not in seen and len(n) >= 2:
                    key_elems.append(f"keyword:{n}")
                    seen.add(n)
                if len(key_elems) >= 6:
                    break
            if not data_matches:
                key_elems.append("quote_text")
            key_elems.append("glow")

            # 根据内容选择视觉类型
            visual_type = detect_visual_type(content)

            storyboard.append({
                "scene_id": i + 1,
                "concept": talking_point or content[:80],
                "mood": "专业、有冲击力、现代感",
                "visual_type": visual_type,
                "choreography": {
                    "title": f"{title_verbs[i % len(title_verbs)]} in from left",
                    "subtitle": "CASCADE in staggered 0.2s",
                    "content": f"{content_verbs[i % len(content_verbs)]} gently",
                },
                "transition_in": "hard_cut" if i == 0 else "velocity_upward",
                "transition_out": "hard_cut" if i == len(sections) - 1 else "velocity_upward",
                "depth_layers": depth_variants[i % len(depth_variants)],
                "density_target": 8,
                "key_elements": key_elems[:6],
                "narration": content,
            })

    # 补充每个场景的配音文案和时间戳
    for i, scene_data in enumerate(storyboard):
        if i < len(sections):
            section = sections[i]
            # 新格式用content，旧格式用voiceover
            scene_data["voiceover_text"] = section.get("content", "") or section.get("voiceover", "")
            scene_data["scene_id"] = i + 1

            # 添加时间戳
            if i < len(matched_timestamps):
                scene_data["timestamp"] = matched_timestamps[i]
            elif "timestamp" not in scene_data:
                # 估算时间戳
                voiceover = scene_data.get("voiceover_text", "")
                duration = max(len(voiceover) * 0.2, 5)
                start = sum(s.get("duration", 5) for s in storyboard[:i])
                scene_data["timestamp"] = {
                    "start": start,
                    "end": start + duration,
                }

    return storyboard


def run(context: dict) -> dict:
    """主入口：生成storyboard"""

    topic = context.get("topic", "未知话题")
    print(f"  [storyboard] 为 '{topic}' 设计分镜...")


    # 读取script.json
    script_path = context.get("script_path") or str(OUTPUT_DIR / "step03_script.json")
    if not os.path.exists(script_path):
        print(f"  ❌ [storyboard] 找不到脚本文件: {script_path}")
        return context

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    # 读取design.md
    design_md_path = context.get("design_md_path") or str(OUTPUT_DIR / "design.md")
    design_md = ""
    if os.path.exists(design_md_path):
        with open(design_md_path, "r", encoding="utf-8") as f:
            design_md = f.read()
    else:
        print(f"  ⚠️ [storyboard] 找不到design.md，使用默认设计系统")

    # 读取transcript.json（可选）
    transcript_path = context.get("transcript_path") or str(OUTPUT_DIR / "whisperx_transcript.json")
    transcript_data = None
    if os.path.exists(transcript_path):
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)
        print(f"  [storyboard] 加载时间戳: {len(transcript_data.get('segments', []))} 个片段")
    else:
        print(f"  ⚠️ [storyboard] 找不到transcript.json，使用估算时间戳")

    # 读取配音时长（用于动态场景数计算）
    voice_durations = context.get("voice_scene_durations", [])
    total_duration = sum(d.get("duration", 0) for d in voice_durations) if voice_durations else 0
    if total_duration > 0:
        print(f"  [storyboard] 配音总时长: {total_duration:.1f}s")

    # 生成storyboard
    storyboard = generate_storyboard(script_data, design_md, transcript_data, total_duration)
    
    # 转换字段名，匹配hf-builder期望的格式
    for scene in storyboard:
        # voiceover_text → narration
        if "voiceover_text" in scene and "narration" not in scene:
            scene["narration"] = scene.pop("voiceover_text")
        
        # timestamp → duration
        if "timestamp" in scene and "duration" not in scene:
            ts = scene.pop("timestamp")
            if isinstance(ts, dict) and "start" in ts and "end" in ts:
                scene["duration"] = round(ts["end"] - ts["start"], 2)
        
        # choreography → animations
        if "choreography" in scene and "animations" not in scene:
            scene["animations"] = scene.pop("choreography")
        
        # transition_in/transition_out → transition
        if "transition_in" in scene or "transition_out" in scene:
            scene["transition"] = {
                "in": scene.pop("transition_in", ""),
                "out": scene.pop("transition_out", "")
            }
    
    # 用实际配音时长校准场景时长（如果可用）
    # 优先从文件加载（文件是最权威的数据源，context可能有旧run的残留数据）
    vsd_path = OUTPUT_DIR / "voice_scene_durations.json"
    voice_scene_durs = []
    if vsd_path.exists():
        with open(vsd_path, "r", encoding="utf-8") as f:
            voice_scene_durs = json.load(f)
        print(f"  [storyboard] 从文件加载配音时长: {len(voice_scene_durs)} 段")
    if not voice_scene_durs:
        voice_scene_durs = context.get("voice_scene_durations", [])
        if voice_scene_durs:
            print(f"  [storyboard] 从context加载配音时长: {len(voice_scene_durs)} 段")
    if voice_scene_durs and len(voice_scene_durs) == len(storyboard):
        print(f"  [storyboard] 用实际配音时长校准 {len(storyboard)} 个场景...")
        cumulative = 0.0
        for i, scene in enumerate(storyboard):
            actual_dur = voice_scene_durs[i]["duration"]
            scene["duration"] = actual_dur
            scene["start_time"] = round(cumulative, 2)
            cumulative += actual_dur
            scene["end_time"] = round(cumulative, 2)
        print(f"  [storyboard] 校准完成: 总时长 {cumulative:.1f}s")
    elif voice_scene_durs:
        print(f"  ⚠️ [storyboard] 配音场景数({len(voice_scene_durs)}) != 分镜数({len(storyboard)})，跳过校准")

    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(STORYBOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(storyboard, f, ensure_ascii=False, indent=2)
    print(f"  [storyboard] 已保存到: {STORYBOARD_PATH} ({len(storyboard)} 个场景)")

    # 更新context
    context["storyboard_path"] = str(STORYBOARD_PATH)
    context["storyboard"] = storyboard

    return context


if __name__ == "__main__":
    # 测试
    test_context = {
        "topic": "2026高考第一批显眼包出现了",
        "script_path": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/output/step03_script.json",
        "design_md_path": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/output/design.md",
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  场景数: {len(result.get('storyboard', []))}")
