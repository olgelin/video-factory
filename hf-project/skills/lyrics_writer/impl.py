"""
lyrics_writer/impl.py — 歌词生成（深度版）
功能：根据口播稿内容+选题+风格，创作有深度映射的歌词

核心理念：映射哲学
- 表层：具体事件/技术/新闻（观众能理解）
- 深层：人性/情感/社会/存在（观众能共鸣）
- 映射：通过比喻、象征、类比，把具体事件升华为普遍真理

例子：
- AI内容溯源 → 信任的本质（什么是真的？）
- 技术狂奔 → 人类身份焦虑（我是谁？）
- 数字世界 → 现实与虚幻（什么是真实？）
- 信息爆炸 → 意义的寻找（什么值得相信？）

输入：
- output/step03_script.json（口播稿）
- output/topic_selected.json（选题信息）
- output/style_profile.json（风格指导，可选）

输出：output/lyrics.txt（ACE-Step格式歌词）
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
SCRIPT_PATH = OUTPUT_DIR / "step03_script.json"
TOPIC_SELECTED_PATH = OUTPUT_DIR / "topic_selected.json"
STYLE_PROFILE_PATH = OUTPUT_DIR / "style_profile.json"
LYRICS_PATH = OUTPUT_DIR / "lyrics.txt"

# LLM配置
# LLM配置已移至llm_utils.py


def generate_lyrics(script_data: dict, topic_selected: dict = None, 
                   style_profile: dict = None) -> str:
    """根据口播稿+选题+风格，生成有深度映射的歌词"""
    
    topic = script_data.get("topic", "")
    mood = script_data.get("mood", "")
    
    # 提取口播稿全文（兼容新旧格式）
    sections = script_data.get("voiceover_sections", [])
    if not sections:
        sections = script_data.get("scenes", [])
    
    full_text = ""
    section_summaries = []
    for i, section in enumerate(sections):
        content = section.get("content", "") or section.get("voiceover", "")
        talking_point = section.get("talking_point", "") or section.get("visual_hint", "")
        full_text += content + "\n"
        section_summaries.append(f"段落{i+1}: {talking_point[:80] if talking_point else content[:80]}...")
    
    # 构建选题信息
    topic_info = ""
    if topic_selected:
        selected_topic = topic_selected.get("selected_topic", "")
        angle = topic_selected.get("angle", "")
        hook = topic_selected.get("hook", "")
        target_audience = topic_selected.get("target_audience", "")
        topic_info = f"""
选题信息：
- 选定话题：{selected_topic}
- 切入角度：{angle}
- 开头hook：{hook}
- 目标受众：{target_audience}
"""
    
    # 构建风格指导
    style_guide = ""
    if style_profile and not style_profile.get("error"):
        style_name = style_profile.get("style_name", "")
        language = style_profile.get("language_style", {})
        rhythm = style_profile.get("rhythm", {})
        
        style_guide = f"""
风格指导：
- 风格名称：{style_name}
- 语气：{language.get('tone', '口语化')}
- 标志性表达：{'、'.join(language.get('signature_phrases', [])[:3])}
- 情绪弧线：{rhythm.get('emotional_arc', '低→高→升华')}
"""
    
    system_prompt = """你是一个顶级的歌词创作者，擅长「映射哲学」——通过具体事件映射到人性、情感、社会的深层真理。

## 核心理念：双层歌词结构

### 表层（观众能理解）
- 具体事件、技术、新闻
- 真实的数据、时间、人物
- 让观众知道"在讲什么"

### 深层（观众能共鸣）
- 人性、情感、社会、存在
- 普遍的真理、永恒的困惑
- 让观众感受到"这跟我有关"

### 映射技巧
1. **比喻**：把抽象概念具象化
   - "信任" → "锚点"、"灯塔"、"基石"
   - "虚假" → "面具"、"幻影"、"迷雾"
   - "真实" → "光"、"根"、"骨"

2. **象征**：用具体事物代表抽象概念
   - 身份证 → 信任的证明
   - 水印 → 不可磨灭的真相
   - 镜子 → 自我认知

3. **类比**：把技术问题映射到人生问题
   - AI造假 → 人与人之间的欺骗
   - 信息过载 → 意义的迷失
   - 技术狂奔 → 人性的滞后

4. **悖论**：揭示表面与本质的矛盾
   - 越智能越不信任
   - 越连接越孤独
   - 越自由越迷茫

## 歌词结构（副歌开头，像徐良/汪苏泷风格）

### 结构模板（副歌开头）
[Chorus] - 副歌开头！一上来就抓住听众，最核心最抓人的部分
[Verse 1] - 主歌1，表层展开（具体事件/技术/数据）
[Chorus] - 副歌重复，强化记忆点
[Verse 2] - 主歌2，深层映射（人性/情感/社会）
[Chorus] - 副歌第三次，情绪最高点
[Bridge] - 桥段，哲学升华（悖论/真理/顿悟）
[Chorus] - 副歌收尾，最后一次强化
[Outro] - 尾声，余韵收束

### 关键原则
1. **副歌必须开头**：第一段就是副歌！像流行歌曲一上来就抓住听众
2. **副歌要重复**：至少出现3-4次，强化记忆
3. **副歌要抓人**：朗朗上口，能记住，能跟着唱
4. **每段要饱满**：不要凑字数，要有实质内容和情感
5. **不限长度**：根据内容自然展开，该长就长

### 情绪弧线
- Chorus（开头）：冲击+核心（高）
- Verse 1：讲述+分析（中）
- Chorus（重复）：强化（高）
- Verse 2：映射+共鸣（中→高）
- Chorus（高潮）：情绪最高点（最高）
- Bridge：升华+顿悟（高→低→高）
- Chorus（收尾）：收束+记忆（最高）
- Outro：余韵（渐弱）

## 创作要求

1. **表层要具体**：有真实的数据、事件、人物
2. **深层要普世**：能引发情感共鸣、哲学思考
3. **映射要自然**：不能生硬，要像水到渠成
4. **语言要诗意**：但不要太文艺，要口语化
5. **副歌要抓人**：朗朗上口，能记住，能跟着唱
6. **长度不限**：根据内容自然展开，不要凑字数也不要刻意精简

## 输出格式
直接输出歌词文本，不要其他内容。用方括号标注结构。"""

    prompt = f"""口播稿主题: {topic}
口播稿情绪: {mood}
{topic_info}
{style_guide}
口播稿内容摘要:
{chr(10).join(section_summaries[:6])}

口播稿全文:
{full_text[:2000]}

请用「映射哲学」创作歌词：
1. 表层：讲清楚这个事件/技术是什么
2. 深层：映射到人性/情感/社会的深层真理
3. 用比喻、象征、类比把具体升华为普遍
4. 副歌开头！一上来就是最抓人的副歌（像徐良/汪苏泷的流行歌曲风格）
5. 副歌至少重复3-4次，强化记忆
6. 长度不限，根据内容自然展开

直接输出歌词，不要其他内容。"""

    response = call_llm(prompt, system_prompt, max_tokens=4000)
    
    if not response:
        return _generate_fallback_lyrics(topic, sections)
    
    # 清理响应
    lyrics = response.strip()
    lyrics = re.sub(r'^```\w*\s*', '', lyrics)
    lyrics = re.sub(r'```\s*$', '', lyrics).strip()
    
    # 确保有结构标签
    if not re.search(r'\[.*?\]', lyrics):
        lines = lyrics.split('\n')
        if len(lines) > 4:
            lyrics = f"[Chorus]\n{lines[0]}\n{lines[1]}\n\n[Verse 1]\n" + '\n'.join(lines[2:])
    
    return lyrics


def _generate_fallback_lyrics(topic: str, sections: list) -> str:
    """生成fallback歌词（带映射哲学）"""
    
    key_sentences = []
    for section in sections[:4]:
        content = section.get("content", "") or section.get("voiceover", "")
        first_sentence = content.split('。')[0] if content else ""
        if first_sentence and len(first_sentence) > 5:
            key_sentences.append(first_sentence)
    
    if not key_sentences:
        key_sentences = [topic]
    
    # 带映射的fallback
    lyrics = f"""[Chorus]
{key_sentences[0] if key_sentences else topic}
真相与谎言之间，只隔着一层看不见的线
我们都在寻找，那道能穿透迷雾的光
{key_sentences[0] if key_sentences else topic}
信任不是天生的，是需要被证明的信仰

[Verse 1]
{key_sentences[1] if len(key_sentences) > 1 else '时代的浪潮滚滚向前'}
数据在流动，信息在爆炸
我们站在十字路口，不知该相信谁
每一个选择都关乎未来
每一天都有新的发现

[Verse 2]
面具戴久了，会忘记真实的自己
幻影看多了，会迷失在虚幻里
我们渴望真实，却又害怕被看穿
这是人性的悖论，也是时代的困境

[Bridge]
{key_sentences[2] if len(key_sentences) > 2 else '不要害怕改变'}
当技术狂奔，人性却在原地踏步
我们需要的不是更快的AI
而是更真的心

[Outro]
记住，信任不是天生的
是需要被证明的信仰
在这个真假难辨的世界
做那个敢于摘下面具的人
"""
    return lyrics


def run(context: dict) -> dict:
    """主入口：生成歌词"""
    
    print(f"  [lyrics-writer] 开始生成歌词...")
    
    
    # 读取口播稿
    script_path = context.get("script_path") or str(SCRIPT_PATH)
    if not os.path.exists(script_path):
        print(f"  ❌ [lyrics-writer] 找不到口播稿: {script_path}")
        return context
    
    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)
    
    topic = script_data.get("topic", "")
    sections_count = len(script_data.get("voiceover_sections", [])) or len(script_data.get("scenes", []))
    print(f"  [lyrics-writer] 口播稿主题: {topic}")
    print(f"  [lyrics-writer] 段落数: {sections_count}")
    
    # 读取选题信息（如果有）
    topic_selected = None
    topic_selected_path = context.get("topic_selected_path") or str(TOPIC_SELECTED_PATH)
    if os.path.exists(topic_selected_path):
        with open(topic_selected_path, "r", encoding="utf-8") as f:
            topic_selected = json.load(f)
        print(f"  [lyrics-writer] 选题: {topic_selected.get('selected_topic', 'N/A')}")
    
    # 读取风格配置（如果有）
    style_profile = None
    style_profile_path = context.get("style_profile_path") or str(STYLE_PROFILE_PATH)
    if os.path.exists(style_profile_path):
        with open(style_profile_path, "r", encoding="utf-8") as f:
            style_profile = json.load(f)
        print(f"  [lyrics-writer] 风格: {style_profile.get('style_name', 'N/A')}")
    
    # 生成歌词
    lyrics = generate_lyrics(script_data, topic_selected, style_profile)
    
    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(LYRICS_PATH, "w", encoding="utf-8") as f:
        f.write(lyrics)
    
    # 统计
    lines = [l for l in lyrics.split('\n') if l.strip() and not l.strip().startswith('[')]
    chars = sum(len(l) for l in lines)
    
    print(f"  [lyrics-writer] ✅ 歌词生成完成")
    print(f"    行数: {len(lines)}")
    print(f"    字数: {chars}")
    print(f"    已保存到: {LYRICS_PATH}")
    
    # 更新context
    context["lyrics_path"] = str(LYRICS_PATH)
    context["lyrics"] = lyrics
    
    return context


if __name__ == "__main__":
    test_context = {}
    result = run(test_context)
    
    print(f"\n✅ 测试完成")
    print(f"  歌词长度: {len(result.get('lyrics', ''))} 字符")
