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

## 歌词（共{len(lyrics_lines)}行）
{lyrics_summary}

请为上面的歌词设计视觉概念。要求：
- 每组1-2行歌词配一个视觉概念
- visual_type 从可用类型中选择
- 每个概念必须包含教学相关的视觉元素 + 歌词文字
- 输出恰好 {len(lyrics_lines)} 个概念的 JSON 数组
- 只输出 JSON"""

    print(f"  [lyric-scene-designer] 为 {len(lyrics_lines)} 行歌词设计视觉概念...")

    response = call_llm(prompt, system_prompt, max_tokens=4000)

    # 解析
    concepts = []
    if response:
        try:
            cleaned = re.sub(r"```json\s*", "", response)
            cleaned = re.sub(r"```\s*$", "", cleaned).strip()
            json_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if json_match:
                concepts = json.loads(json_match.group())
        except json.JSONDecodeError:
            print("  ⚠️ [lyric-scene-designer] JSON解析失败")

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
