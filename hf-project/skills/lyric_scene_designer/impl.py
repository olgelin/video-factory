"""
lyric_scene_designer — BGM歌词段视觉概念设计

职责：一次LLM调用，为所有歌词组生成知识+歌词融合的视觉概念
输入：lyrics.txt + step03_script.json(topic) + design.md(风格)
输出：lyric_scenes.json（visual_type + concept + key_elements）
"""

import os
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from llm_utils import call_llm

_PROMPTS_DIR = Path(__file__).parent / "prompts"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def _repair_truncated_json(json_str: str) -> str:
    """修复被截断的JSON数组：移除尾部不完整对象，补上缺失的闭合符号"""
    # 计算未闭合的括号
    open_braces = json_str.count('{') - json_str.count('}')
    open_brackets = json_str.count('[') - json_str.count(']')

    if open_braces <= 0 and open_brackets <= 0:
        return json_str

    # 如果有未闭合的 {，说明最后一个对象不完整 → 移除它
    if open_braces > 0:
        last_open_brace = json_str.rfind('{')
        # 找到它之前的逗号（即前一个完整对象的结束位置）
        cut = json_str.rfind(',', 0, last_open_brace)
        if cut > 0:
            json_str = json_str[:cut]
            # 重新计算
            open_braces = json_str.count('{') - json_str.count('}')
            open_brackets = json_str.count('[') - json_str.count(']')

    # 补闭合：去尾部逗号 + 补括号
    json_str = json_str.rstrip().rstrip(',')
    json_str += '}' * max(0, open_braces) + ']' * max(0, open_brackets)
    return json_str


def _load_prompt(name: str) -> str:
    p = _PROMPTS_DIR / f"{name}.md"
    if not p.exists():
        raise FileNotFoundError(f"Prompt missing: {p}")
    return p.read_text(encoding="utf-8")


def run(context: dict) -> dict:
    """主入口"""

    lyrics_path = context.get("lyrics_path") or str(OUTPUT_DIR / "lyrics.txt")
    script_path = context.get("script_path") or str(OUTPUT_DIR / "step03_script.json")
    design_path = context.get("design_md_path") or str(OUTPUT_DIR / "design.md")

    # 检查输入
    if not os.path.exists(lyrics_path):
        print("  ⚠️ [lyric-scene-designer] 无歌词文件，跳过")
        return context
    if not os.path.exists(script_path):
        print("  ⚠️ [lyric-scene-designer] 无脚本文件，跳过")
        return context

    lyrics_text = Path(lyrics_path).read_text(encoding="utf-8").strip()
    lyrics_lines = [l.strip() for l in lyrics_text.split("\n")
                    if l.strip() and not l.startswith("[") and not l.startswith("#")]

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)
    topic = script_data.get("topic", "未知话题")
    # 提取教学段的核心概念作为视觉参考
    teaching_concepts = []
    for section in script_data.get("voiceover_sections", []):
        tp = section.get("talking_point", "")
        if tp:
            teaching_concepts.append(tp)

    # 读设计系统
    design_md = ""
    if os.path.exists(design_path):
        design_md = Path(design_path).read_text(encoding="utf-8")[:1000]

    # 构建 prompt
    system_prompt = _load_prompt("system")

    lyrics_summary = "\n".join(f"{i+1}. {l}" for i, l in enumerate(lyrics_lines))
    concepts_text = "\n".join(f"- {c}" for c in teaching_concepts[:8])

    prompt = f"""## 教学主题
{topic}

## 教学段核心概念
{concepts_text}

## 视觉风格
{design_md}

## 歌词（共{len(lyrics_lines)}行，风格一致）
{lyrics_summary}

请为这些歌词设计 20 个视觉概念（如果歌词超过20行，按主题分组复用）。要求：
- visual_type 从可用类型中选择
- 每个概念必须包含教学相关的视觉元素 + 歌词文字
- 输出恰好 20 个概念的 JSON 数组
- **只输出 JSON 数组，不要任何解释、思考过程或 markdown 代码块**
- **第一条必须是 "[",最后一个字符必须是 "]"**"""

    print(f"  [lyric-scene-designer] 为 {len(lyrics_lines)} 行歌词设计视觉概念...")

    response = call_llm(prompt, system_prompt, max_tokens=16000, temperature=0.3)

    # 解析
    concepts = []
    if response:
        # DEBUG: 保存 raw 返回用于诊断（截断到 20KB）
        debug_path = OUTPUT_DIR / "lyric_scene_debug.txt"
        debug_path.write_text(response[:20000], encoding="utf-8")
        has_more = len(response) > 20000
        print(f"  [lyric-scene-designer] LLM 返回 {len(response)} 字符 → {debug_path}{' (截断)' if has_more else ''}")

        try:
            # 策略1: 直接找最外层 [...]（最可靠）
            start = response.find('[')
            end = response.rfind(']')
            if start >= 0 and end > start:
                json_str = response[start:end+1]
                # 尝试修复截断的JSON（补上缺失的闭合括号）
                json_str = _repair_truncated_json(json_str)
                concepts = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"  [lyric-scene-designer] 策略1失败: {e}")
            try:
                # 策略2: markdown代码块
                m = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', response)
                if m:
                    concepts = json.loads(m.group(1))
            except json.JSONDecodeError as e2:
                print(f"  [lyric-scene-designer] 策略2失败: {e2}")
                try:
                    # 策略3: 在响应中逐行找JSON片段（处理thinking-model输出）
                    # 找最后一个完整的JSON对象数组片段
                    parts = response.split('\n')
                    json_start = -1
                    for i, line in enumerate(parts):
                        if line.strip().startswith('[') and ('"visual_type"' in line or i > len(parts)*0.3):
                            json_start = i
                            break
                    if json_start >= 0:
                        fragment = '\n'.join(parts[json_start:])
                        end2 = fragment.rfind(']')
                        if end2 > 0:
                            fragment = _repair_truncated_json(fragment[:end2+1])
                            concepts = json.loads(fragment)
                except json.JSONDecodeError as e3:
                    print(f"  [lyric-scene-designer] 策略3失败: {e3}")

    if concepts:
        out_path = OUTPUT_DIR / "lyric_scenes.json"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(concepts, f, ensure_ascii=False, indent=2)
        print(f"  ✅ [lyric-scene-designer] 生成 {len(concepts)} 个视觉概念 → {out_path}")
        context["lyric_scenes_path"] = str(out_path)
    else:
        print("  ⚠️ [lyric-scene-designer] 未生成有效概念，storyboard_lyric 将用默认模板")

    return context
