"""
script_writer/impl.py — 口播脚本生成器
功能：根据topic-selector的选题结果，生成符合风格的口播脚本

职责边界：
- 只负责口播文案（纯文本+段落划分）
- 不负责视觉设计（那是storyboard的事）
- 不负责场景划分（那是storyboard的事）

输入：output/topic_selected.json（topic-selector的输出）
输出：output/step03_script.json（口播脚本）

输出格式：
{
  "topic": "话题",
  "mood": "整体情绪",
  "voiceover_sections": [
    {
      "section_id": 1,
      "content": "口播文案段落",
      "talking_point": "这个段落的核心主题（给storyboard参考）"
    }
  ],
  "total_chars": 575
}

风格规范（深度学者风）：
- 像一个研究深入、体贴关心的学者在跟你聊天
- 有独立思考，能看到别人看不到的角度
- 善用隐喻、反差、类比来解释复杂问题
- 不要用模板化的固定表达，每期语言应该自然不同
- 要有冲突感、反差感、悬念感
"""

import os
import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from llm_utils import call_llm

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
TOPIC_SELECTED_PATH = OUTPUT_DIR / "topic_selected.json"
SCRIPT_PATH = OUTPUT_DIR / "step03_script.json"
STYLE_PROFILE_PATH = OUTPUT_DIR / "style_profile.json"

# === Prompt 加载 ===
_PROMPTS_DIR = Path(__file__).parent / "prompts"

def _load_prompt(name: str) -> str:
    p = _PROMPTS_DIR / f"{name}.md"
    if not p.exists():
        raise FileNotFoundError(f"Prompt missing: {p}")
    return p.read_text(encoding="utf-8")

# LLM配置已移至llm_utils.py

# 数字转中文映射
DIGIT_MAP = {
    '0': '零', '1': '一', '2': '二', '3': '三', '4': '四',
    '5': '五', '6': '六', '7': '七', '8': '八', '9': '九',
}

# 常见数字词（按key长度降序排列，避免10000000先于100000000被匹配）
_NUMBER_WORDS_RAW = {
    '100000000': '一亿',
    '10000000': '一千万',
    '1000000': '一百万',
    '500000': '五十万', '200000': '二十万',
    '100000': '十万', '50000': '五万', '20000': '两万',
    '10000': '一万',
    '8000': '八千', '5000': '五千', '3000': '三千', '2000': '两千',
    '1000': '一千', '100': '一百',
}
NUMBER_WORDS = dict(sorted(_NUMBER_WORDS_RAW.items(), key=lambda x: -len(x[0])))


def preprocess_numbers(text: str) -> str:
    """数字转中文读法"""
    for num, word in NUMBER_WORDS.items():
        text = text.replace(num, word)

    def replace_percent(m):
        num = m.group(1)
        # 处理小数：4.5 → 四点五
        if '.' in num:
            parts = num.split('.')
            integer_part = ''.join(DIGIT_MAP.get(d, d) for d in parts[0])
            decimal_part = ''.join(DIGIT_MAP.get(d, d) for d in parts[1])
            return f"百分之{integer_part}点{decimal_part}"
        return f"百分之{num}"

    # 匹配带小数的百分比：4.5% 或 45%
    text = re.sub(r'(\d+\.?\d*)%', replace_percent, text)

    def replace_number(m):
        num = m.group(0)
        if len(num) == 4 and num.startswith('20'):
            return num
        result = ''
        for d in num:
            result += DIGIT_MAP.get(d, d)
        return result

    text = re.sub(r'\d+', replace_number, text)

    return text


def preprocess_text(text: str) -> str:
    """预处理配音文本（只处理标点，数字由voice_gen的text_preprocessor处理）"""
    # 半角标点转全角（中文TTS标准）
    punct_map = {',': '，', '.': '。', '!': '！', '?': '？',
                 ':': '：', ';': '；', '(': '（', ')': '）'}
    for half, full in punct_map.items():
        text = text.replace(half, full)
    text = re.sub(r'\s+', ' ', text).strip()

    return text





def generate_script(topic_selected: dict, style_profile: dict = None, research_data: str = "", video_style: str = "news") -> dict:
    """根据选题结果生成口播脚本（纯文案，不含视觉设计）"""
    
    selected_topic = topic_selected.get("selected_topic", "")
    angle = topic_selected.get("angle", "")
    hook = topic_selected.get("hook", "")
    key_points = topic_selected.get("key_points", [])
    target_audience = topic_selected.get("target_audience", "")
    
    # 构建关键点文本
    key_points_text = ""
    for i, kp in enumerate(key_points, 1):
        if isinstance(kp, dict):
            point = kp.get("point", "")
            data = kp.get("data", "")
            key_points_text += f"{i}. {point}"
            if data:
                key_points_text += f"（数据：{data}）"
            key_points_text += "\n"
        else:
            key_points_text += f"{i}. {kp}\n"
    
    # 构建风格指导（如果有学习到的风格）
    style_guide = ""
    if style_profile and not style_profile.get("error"):
        style_name = style_profile.get("style_name", "")
        style_desc = style_profile.get("description", "")
        opening = style_profile.get("opening_style", {})
        language = style_profile.get("language_style", {})
        rhythm = style_profile.get("rhythm", {})
        closing = style_profile.get("closing_style", {})
        
        style_guide = f"""

## 学习到的风格：{style_name}
风格描述：{style_desc}

### 开场风格
- 模式：{opening.get('pattern', '设问/冲突')}
- 示例：{'、'.join(opening.get('examples', [])[:2])}

### 语言风格
- 语气：{language.get('tone', '口语化')}
- 口语化程度：{language.get('oral_level', 7)}/10
- 标志性表达：{'、'.join(language.get('signature_phrases', [])[:3])}
- 禁忌：{'、'.join(language.get('forbidden_phrases', [])[:2])}

### 节奏感
- 句式：{rhythm.get('sentence_pattern', '短长交替')}
- 过渡：{rhythm.get('transition_style', '自然过渡')}
- 情绪弧线：{rhythm.get('emotional_arc', '低→高→升华')}

### 结尾风格
- 模式：{closing.get('pattern', '金句升华')}
- 示例：{'、'.join(closing.get('examples', [])[:2])}
"""
    
    # V7: 从 prompts/{style}/script_system.md 加载（统一 prompts 目录）
    prompts_root = Path(__file__).parent.parent.parent / "prompts"
    style_dir = video_style if video_style in ("edu", "news", "music", "edu_music") else "news"
    system_path = prompts_root / style_dir / "script_system.md"
    if system_path.exists():
        system_prompt = system_path.read_text(encoding="utf-8").format(style_guide=style_guide)
        print(f"  [script-writer] 使用提示词: prompts/{style_dir}/script_system.md")
    else:
        # 兼容旧位置
        sys_name = "edu_system" if video_style == "edu" else "system"
        system_prompt = _load_prompt(sys_name).format(style_guide=style_guide)
        print(f"  [script-writer] 使用提示词(旧): {sys_name}.md")

    research_section = ""
    if research_data:
        research_section = "\n\n## 真实数据（必须在脚本中引用）:\n" + research_data + "\n"
    prompt = _load_prompt("topic").format(
        selected_topic=selected_topic,
        angle=angle,
        target_audience=target_audience,
        research_section=research_section,
        key_points_text=key_points_text,
    )

    llm_response = call_llm(prompt, system_prompt, max_tokens=8000)

    if not llm_response:
        print("  ❌ [script-writer] LLM返回为空")
        return None

    # 解析JSON（多层fallback）
    result = _parse_json_response(llm_response)
    if result:
        return result
    
    # V39: 重试多次（deepseek-v4-flash reasoning 随机暴走导致 content 为空）
    for attempt in range(3):
        print(f"  ⚠️ [script-writer] JSON解析失败，重试 {attempt+1}/3...")
        strict_prompt = prompt + "\n\n重要：只输出纯JSON，不要任何markdown代码块，不要任何解释文字。"
        llm_response = call_llm(strict_prompt, system_prompt, max_tokens=8000)
        if llm_response:
            result = _parse_json_response(llm_response)
            if result:
                return result
    
    print("  ❌ [script-writer] JSON解析失败（重试3次）")
    return None


def _parse_json_response(llm_response: str) -> dict:
    """多层JSON解析"""
    ALLOWED_VISUAL_HINTS = {"data_impact", "timeline_event", "compare", "quote_hero", "flow", "hud", "list_alert", "code_terminal", "ranking_board", "product_showcase", "explain_card", "example_showcase", "step_reveal", "keyword_highlight", "practice_prompt", "summary_grid"}
    
    def _validate_section(section: dict, idx: int) -> dict:
        """验证并补全段落字段"""
        section["content"] = preprocess_text(section.get("content", ""))
        # visual_hint: 验证 → 内容检测 → 多样化默认
        vh = section.get("visual_hint", "")
        if vh not in ALLOWED_VISUAL_HINTS:
            # 用内容关键词检测
            text = section.get("content", "") + " " + section.get("talking_point", "")
            vh = _detect_visual_hint_from_text(text, idx)
        section["visual_hint"] = vh
        section.setdefault("rhythm_hint", "medium")
        section.setdefault("emotion_intensity", 5)
        section.setdefault("transition_hint", "无")
        return section
    
    def _detect_visual_hint_from_text(text: str, idx: int) -> str:
        """根据文本内容检测最合适的visual_hint"""
        t = text.lower()
        if any(k in t for k in ["%", "数据", "统计", "数字", "万", "亿", "增长", "下降"]):
            return "data_impact"
        if any(k in t for k in ["之后", "随后", "最终", "回顾", "历史", "演变", "发展"]):
            return "timeline_event"
        if any(k in t for k in ["vs", "对比", "相反", "但是", "然而", "不同于", "一方面"]):
            return "compare"
        if any(k in t for k in ["说", "怒斥", "质问", "声明", "金句", "名言", "观点"]):
            return "quote_hero"
        if any(k in t for k in ["因为", "所以", "导致", "原因", "结果", "逻辑", "链条"]):
            return "flow"
        if any(k in t for k in ["排名", "排行", "第一", "领先", "超越", "竞争"]):
            return "ranking_board"
        # 多样化默认：8种类型轮转
        defaults = ["data_impact", "compare", "flow", "quote_hero", "timeline_event", "hud", "list_alert", "ranking_board"]
        return defaults[idx % len(defaults)]
    
    # Layer 1: 去除markdown代码块
    cleaned = re.sub(r'```json\s*', '', llm_response)
    cleaned = re.sub(r'```\s*$', '', cleaned).strip()
    
    # Layer 2: 尝试直接解析
    try:
        script = json.loads(cleaned)
        if "voiceover_sections" in script:
            for i, section in enumerate(script.get("voiceover_sections", [])):
                _validate_section(section, i)

            return script
        elif "scenes" in script:
            return _convert_scenes_to_sections(script)
    except json.JSONDecodeError:
        pass
    
    # Layer 3: 正则匹配最外层JSON
    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if json_match:
        try:
            script = json.loads(json_match.group())
            if "voiceover_sections" in script:
                for i, section in enumerate(script.get("voiceover_sections", [])):
                    _validate_section(section, i)
                return script
            elif "scenes" in script:
                return _convert_scenes_to_sections(script)
        except json.JSONDecodeError:
            pass
    
    # Layer 4: 提取所有JSON对象，找含voiceover_sections或scenes的那个
    i = 0
    while i < len(cleaned):
        start = cleaned.find('{', i)
        if start == -1:
            break
        depth = 0
        end = start
        for j in range(start, min(len(cleaned), start + 10000)):
            if cleaned[j] == '{':
                depth += 1
            elif cleaned[j] == '}':
                depth -= 1
                if depth == 0:
                    end = j + 1
                    break
        try:
            candidate = json.loads(cleaned[start:end])
            if "voiceover_sections" in candidate:
                for i, section in enumerate(candidate.get("voiceover_sections", [])):
                    _validate_section(section, i)
                print(f"  ✅ [script-writer] Layer4 fallback提取成功")
                return candidate
            elif "scenes" in candidate:
                print(f"  ✅ [script-writer] Layer4 fallback提取成功（scenes格式）")
                return _convert_scenes_to_sections(candidate)
        except json.JSONDecodeError:
            pass
        i = start + 1
    
    # Layer 5: 修复常见JSON问题后重试
    fixed = re.sub(r',\s*}', '}', cleaned)
    fixed = re.sub(r',\s*]', ']', fixed)
    fixed = re.sub(r'//.*$', '', fixed, flags=re.MULTILINE)
    # 尝试解析修复后的整个内容
    try:
        script = json.loads(fixed)
        if "voiceover_sections" in script:
            for i, section in enumerate(script.get("voiceover_sections", [])):
                _validate_section(section, i)
            print(f"  ✅ [script-writer] Layer5 修复后解析成功")
            return script
    except json.JSONDecodeError:
        pass
    
    return None


def _convert_scenes_to_sections(script: dict) -> dict:
    """兼容旧格式：将scenes转换为voiceover_sections"""
    scenes = script.get("scenes", [])
    sections = []
    for i, scene in enumerate(scenes):
        voiceover = scene.get("voiceover", "")
        visual_hint = scene.get("visual_hint", "")
        sections.append({
            "section_id": i + 1,
            "content": preprocess_text(voiceover),
            "talking_point": visual_hint[:50] if visual_hint else f"段落{i+1}"
        })
    
    return {
        "topic": script.get("topic", ""),
        "mood": script.get("mood", ""),
        "voiceover_sections": sections,
        "total_chars": sum(len(s.get("content", "")) for s in sections)
    }


def run(context: dict) -> dict:
    """主入口：生成口播脚本"""

    print(f"  [script-writer] 开始生成口播脚本...")

    # 加载环境变量

    # 读取topic-selector的输出
    topic_selected_path = context.get("topic_selected_path") or str(TOPIC_SELECTED_PATH)
    if not os.path.exists(topic_selected_path):
        print(f"  ❌ [script-writer] 找不到选题文件: {topic_selected_path}")
        return context

    with open(topic_selected_path, "r", encoding="utf-8") as f:
        topic_selected = json.load(f)

    selected_topic = topic_selected.get("selected_topic", "")
    angle = topic_selected.get("angle", "")
    hook = topic_selected.get("hook", "")

    print(f"  [script-writer] 选题: {selected_topic}")
    print(f"  [script-writer] 角度: {angle}")
    print(f"  [script-writer] hook: {hook}")

    # 读取风格配置（如果有）
    style_profile = None
    style_profile_path = context.get("style_profile_path") or str(STYLE_PROFILE_PATH)
    if os.path.exists(style_profile_path):
        with open(style_profile_path, "r", encoding="utf-8") as f:
            style_profile = json.load(f)
        print(f"  [script-writer] 使用风格: {style_profile.get('style_name', 'N/A')}")
    else:
        print(f"  [script-writer] 使用默认风格")

    # 生成脚本 — 将key_points数据作为research_data传入
    research_data = ""
    for kp in topic_selected.get("key_points", []):
        if isinstance(kp, dict):
            point = kp.get("point", "")
            data = kp.get("data", "")
            source = kp.get("source", "")
            if point and data:
                research_data += f"- {point} [数据: {data}] (来源: {source})\n"
    
    # V6: edu 模式用教师风格
    video_style = context.get("video_style", "news")
    script = generate_script(topic_selected, style_profile, research_data, video_style)

    if not script:
        print("  ❌ [script-writer] 脚本生成失败")
        # 删除旧脚本，防止CRITICAL_CHECKS误通过
        if SCRIPT_PATH.exists():
            SCRIPT_PATH.unlink()
            print(f"  🗑️ [script-writer] 已删除旧脚本: {SCRIPT_PATH}")
        return context

    # 验证脚本质量（防止LLM输出被错误解析）
    sections = script.get("voiceover_sections", [])
    if len(sections) < 3 or len(sections) > 20:
        print(f"  ❌ [script-writer] 段落数异常: {len(sections)}（期望5-15）")
        return context
    # 检查每个段落是否有足够内容
    short_sections = [s for s in sections if len(s.get("content", "")) < 10]
    if len(short_sections) > len(sections) * 0.3:
        print(f"  ❌ [script-writer] 过多短段落: {len(short_sections)}/{len(sections)}")
        return context

    # === V5.2 Fix: 话题一致性验证 ===
    # LLM 可能被旧 context 污染，生成完全不相关的话题
    script_topic = script.get("topic", "")
    if selected_topic and script_topic:
        # 提取关键词做模糊匹配（处理中文破折号、英文横线等分隔符）
        import re as _re_kw
        def _extract_kw(text):
            # 非中文/字母/数字（标点、括号等）→ 空格
            text = _re_kw.sub(r'[^\w\u4e00-\u9fff]+', ' ', text)
            # 中英文边界、数字边界插入空格（让 "OpenAI下一代模型GPT-6" → "OpenAI 下一代模型 GPT-6"）
            text = _re_kw.sub(r'(?<=[\u4e00-\u9fff])(?=[A-Za-z0-9])', ' ', text)
            text = _re_kw.sub(r'(?<=[A-Za-z0-9])(?=[\u4e00-\u9fff])', ' ', text)
            # 过滤过短 token（单字符如 "的""是" 不算关键词）
            return set(w for w in _re_kw.sub(r'\s+', ' ', text).split() if len(w) > 1)
        input_keywords = _extract_kw(selected_topic)
        script_keywords = _extract_kw(script_topic)
        overlap = input_keywords & script_keywords
        # edu_music topics contain grade/lesson context that LLM naturally paraphrases;
        # 1 shared keyword (e.g. "被动语态") is sufficient to confirm relevance
        min_overlap = 1 if any('\u4e00' <= c <= '\u9fff' for c in selected_topic) else 2
        if len(overlap) < min_overlap and len(input_keywords) > 3:
            print(f"  ❌ [script-writer] 话题不一致！输入={selected_topic[:40]}，输出={script_topic[:40]}，重叠词={overlap}")
            if SCRIPT_PATH.exists():
                SCRIPT_PATH.unlink()
            return context

    # 统计
    total_chars = sum(len(s.get("content", "")) for s in sections)
    print(f"  [script-writer] 生成 {len(sections)} 个段落，{total_chars} 字")

    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SCRIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"  [script-writer] 已保存到: {SCRIPT_PATH}")

    # 更新context
    context["script_path"] = str(SCRIPT_PATH)
    context["script_data"] = script
    context["section_count"] = len(sections)
    context["total_chars"] = total_chars

    return context


if __name__ == "__main__":
    test_context = {}
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  段落数: {result.get('section_count')}")
    print(f"  字数: {result.get('total_chars')}")
