"""
speech_processor/impl.py — 口语转脚本处理器

功能：接收用户说的一段口语（文字），
      清洗 → 纠错 → 提炼核心观点 → 理清逻辑顺序 → 输出结构化脚本

输入：context["speech_text"] — 用户说的原话（文本，可碎片、啰嗦、有错词）
输出：output/step03_script.json — 与 script_writer 完全相同的格式

输出格式（与 script_writer 一致）：
{
  "topic": "提炼后的标题",
  "mood": "整体情绪",
  "voiceover_sections": [
    {"section_id": 1, "content": "段落口播", "talking_point": "这段的核心主题"}
  ],
  "total_chars": 575
}
"""

import os
import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from llm_utils import call_llm

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
SCRIPT_PATH = OUTPUT_DIR / "step03_script.json"
SPEECH_INPUT_PATH = OUTPUT_DIR / "speech_input.txt"


def _load_system_prompt() -> str:
    """从 prompts/speech_system.md 读取 system prompt（不硬编码）"""
    prompt_file = Path(__file__).parent / "prompts" / "speech_system.md"
    try:
        return prompt_file.read_text(encoding="utf-8")
    except Exception:
        return "你是视频内容策划兼文字编辑，把口语清洗重构为结构化口播脚本，输出 JSON。"


def run(context: dict) -> dict:
    """主入口：口语 → 清洗 → 脚本"""

    print(f"  [speech-processor] 开始处理口语输入...")

    speech_text = context.get("speech_text", "")

    # 如果没有通过 context 传入，尝试从文件读取
    if not speech_text and SPEECH_INPUT_PATH.exists():
        speech_text = SPEECH_INPUT_PATH.read_text(encoding="utf-8")
        print(f"  [speech-processor] 从文件读入口语 ({len(speech_text)} 字)")

    if not speech_text:
        print("  ❌ [speech-processor] 没有口语输入")
        return context

    print(f"  [speech-processor] 输入长度: {len(speech_text)} 字")

    # ── 预处理：扔掉纯垃圾 ──
    cleaned = _basic_clean(speech_text)
    if len(cleaned) < 10:
        print("  ❌ [speech-processor] 清洗后内容太少")
        return context

    # ── LLM 深度处理：清洗+纠错+提炼+结构化 ──
    script = _process_with_llm(cleaned)

    if not script:
        print("  ❌ [speech-processor] LLM 处理失败")
        return context

    # ── 验证 ──
    sections = script.get("voiceover_sections", [])
    if len(sections) < 2:
        print(f"  ❌ [speech-processor] 段落太少: {len(sections)}")
        return context

    total_chars = sum(len(s.get("content", "")) for s in sections)
    print(f"  [speech-processor] 提炼完成: {len(sections)} 段, {total_chars} 字")
    print(f"  [speech-processor] 标题: {script.get('topic', '未生成')}")

    # ── 保存 ──
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SCRIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"  [speech-processor] 已保存: {SCRIPT_PATH}")

    # 更新 context 供下游使用
    context["script_path"] = str(SCRIPT_PATH)
    context["script_data"] = script
    context["section_count"] = len(sections)
    context["total_chars"] = total_chars
    # V2: 把 topic 写回 context（否则下游 visual_checker/publish_meta 拿到的 topic 是 None）
    if script.get("topic"):
        context["topic"] = script["topic"]

    return context


def _basic_clean(text: str) -> str:
    """轻度预处理：去掉明显的纯噪音"""
    # 合并多个空格和换行
    text = re.sub(r'\s+', ' ', text).strip()
    # 去掉纯标点/符号行
    lines = [l for l in text.split('\n') if any('\u4e00' <= c <= '\u9fff' for c in l)]
    return '\n'.join(lines)


def _process_with_llm(raw_text: str) -> dict:
    """LLM 深度处理：口语 → 结构化脚本"""

    system_prompt = _load_system_prompt()

    user_prompt = f"""请深度处理以下口语原文，清洗、增强、重构为有冲击力的视频脚本。

===== 原文开始 =====
{raw_text}
===== 原文结束 =====

请直接输出 JSON（包含 topic/mood/audience/emotional_arc/voiceover_sections）。"""

    llm_response = call_llm(user_prompt, system_prompt, max_tokens=4000)

    if not llm_response:
        return None

    return _parse_json(llm_response)


def _parse_json(response: str) -> dict:
    """多层 JSON 解析"""
    cleaned = re.sub(r'```json\s*', '', response)
    cleaned = re.sub(r'```\s*$', '', cleaned).strip()

    # 尝试直接解析
    try:
        data = json.loads(cleaned)
        if "voiceover_sections" in data:
            return data
    except json.JSONDecodeError:
        pass

    # 正则提取最外层 JSON
    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            if "voiceover_sections" in data:
                return data
        except json.JSONDecodeError:
            pass

    # 修复常见错误后重试
    fixed = re.sub(r',\s*}', '}', cleaned)
    fixed = re.sub(r',\s*]', ']', fixed)
    try:
        data = json.loads(fixed)
        if "voiceover_sections" in data:
            return data
    except json.JSONDecodeError:
        pass

    return None


if __name__ == "__main__":
    # 测试
    test_speech = """
    就是那个，我想说一下这个AI这个事情啊，
    现在很多人都在讲AI，但其实好多人就是跟风嘛，
    然后真正懂的人其实不多。
    像那个DeepSeek出来之后，大家都很兴奋，
    就说中国也有自己的大模型了是吧。
    但其实这个东西背后还是有很多问题的，
    比如说算力的问题、数据的问题，
    还有那个就是应用场景到底在哪。
    对，大概就是这个意思。
    """
    ctx = {"speech_text": test_speech}
    result = run(ctx)
    print(f"\n✅ 测试完成")
    print(f"  段落数: {result.get('section_count', 0)}")
    print(f"  字数: {result.get('total_chars', 0)}")
