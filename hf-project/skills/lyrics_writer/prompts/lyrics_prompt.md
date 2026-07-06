口播稿主题: {topic}
口播稿情绪: {mood}
{topic_info}
{style_guide}
口播稿内容摘要:
{chr(10).join(section_summaries[:6])}

口播稿全文:
{full_text[:2000]}

请用「映射哲学 + 遗憾美学」创作歌词：
⏸ 1. 表层：讲清楚这个事件/技术是什么
2. 深层：映射到人性/情感/社会的深层真理
3. 用比喻、象征、类比把具体升华为普遍
4. 🔴 必须有遗憾感：用"若是""可有""不问""别"等句式翻出遗憾
5. 🔴 用日常意象（海/风/花/星球/白鸽乌鸦/节拍）代替直白情绪词
6. 🔴 对话感：像在跟一个人说话，口语化，不要文绉绉
7. 副歌开头！一上来就是最抓人的副歌（参考《起风了》《客官不可以》《PLANET》的抓人感）
8. 副歌至少重复3-4次，强化记忆
9. 长度不限，根据内容自然展开

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
    """主入口：生成歌词