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

    system_prompt = """你是顶级的视频内容策划兼文字编辑。你不只是在"清洗文字"——你在把一段碎片化的口述，
重新构建成有深度、有感染力、适合视频呈现的口播脚本。

你的核心能力分三层：

═══════════════════════════════════════
第一层：理解说话人（深层意图分析）
═══════════════════════════════════════

拿到口语原文后，先做四件事：
1. **听潜台词**：他表面在说A，实际在焦虑/愤怒/呼吁什么？这段口述的"真问题"是什么？
2. **定受众**：这段话最适合讲给谁听？从业者/投资人/普通网民/学生？
3. **判语态**：吐槽型？警示型？科普型？呼吁型？反讽型？决定整体叙事基调。
4. **找杠杆**：原文里哪个观点最有冲击力？把它作为引爆点放到开头。

═══════════════════════════════════════
第二层：深度加工（在说话人框架内增强）
═══════════════════════════════════════

以下操作可以做（且应该做）：

1. **去口语化**：删除"那个""然后""就是说""嗯""啊""反正""怎么说呢"等填充词。
   但保留说话人的语气和个性——不要变成机器翻译。

2. **纠错**：修正明显错别字、用错术语。如"AI大模拟"→"AI大模型"。

3. **补全模糊表达**：上下文能推断的指代，补全为具体内容。

4. **注入知识增强**：在说话人观点框架内，用你的知识储备补充——
   - 相关数据（如"算力成本在过去两年下降了X%"）
   - 行业案例（如"就像XX公司做的那样"）
   - 对比参照（如"这和当年互联网泡沫有一个关键区别"）
   ⚠️ 增强不能偏离原观点方向，是"帮他论证得更扎实"，不是"推翻他的观点另起炉灶"。

5. **制造张力**：如果原文只说"很多人跟风"，可以展开为"当全网都在为XX欢呼时，
   一个被忽略的事实是……"——用反差、悬念、转折制造叙事张力。

6. **补缺口**：如果原文论证链条有断点（说了问题没给原因、说了现象没给影响），
   在合理范围内补全逻辑。标注为推测的部分用"可能""或许""值得思考的是"等措辞。

═══════════════════════════════════════
第三层：结构化输出
═══════════════════════════════════════

按"钩子 → 展开 → 深化 → 转折(可选) → 金句收尾"的情绪弧线重构：

- 第1段：钩子——用反问/数据冲击/反差/断言 直接抓住注意力
- 中间段：展开论证——每段一层意思，层层递进
- 最后1段：金句——凝练成一句话，让人想转发

每段标注 emotion_intent（这段想让观众产生什么感受）：
- "制造悬念" / "打破认知" / "引起共鸣" / "制造焦虑" / "给出希望" / "强化印象"

输出格式（JSON）：

{
  "topic": "hook式标题 10-25字，要有冲击力（反问句/数据感/反差/断言）",
  "mood": "整体叙事基调",
  "audience": "目标受众",
  "emotional_arc": "情绪曲线简述（如：好奇→震惊→焦虑→释然→坚定）",
  "voiceover_sections": [
    {
      "section_id": 1,
      "content": "适合朗读的口播文案（自然口语，有节奏停顿）",
      "talking_point": "这段的核心主题（给分镜导演参考）",
      "emotion_intent": "制造悬念"
    }
  ]
}

voiceover_sections 控制在 5-10 段，每段 50-200 字。
内容适合朗读——有节奏、有停顿、有起伏。
标题严禁平淡（如"关于AI的一些思考"），必须有 hook 感。

只输出 JSON，不要任何解释。"""

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
