"""
style_learner.py — 风格学习器
功能：从样本文案中提炼风格特征，输出风格配置供script-writer使用

用法：
1. 直接输入文案样本文本
2. 或输入多个文案样本，自动融合
3. 输出style_profile.json，script-writer读取后按此风格生成

输入：样本文案（文本或文件路径）
输出：output/style_profile.json（风格配置）
"""

import os
import json
import re
from pathlib import Path

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
STYLE_PROFILE_PATH = OUTPUT_DIR / "style_profile.json"

# LLM配置
LLM_CONFIGS = [
    {
        "name": "mimo",
        "url": "https://token-plan-cn.xiaomimimo.com/v1/chat/completions",
        "model": "mimo-v2.5-pro",
        "env_key": "XIAOMI_API_KEY",
    },
    {
        "name": "deepseek",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
]


def load_env():
    """加载环境变量"""
    from dotenv import load_dotenv
    possible_envs = [
        os.path.join(os.environ.get("HERMES_HOME", ""), ".env"),
        os.path.join(os.environ.get("HERMES_HOME", os.path.expanduser("~")), ".env"),
        os.path.expanduser("~/.env"),
    ]
    for env_path in possible_envs:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            return


import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from llm_utils import call_llm as _shared_call_llm

def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 4000) -> str:
    """调用LLM via shared llm_utils（带中性化+fallback）"""
    return _shared_call_llm(prompt, system_prompt, max_tokens, timeout=180)


def analyze_style(samples: list, sample_names: list = None) -> dict:
    """从样本文案中分析风格特征"""
    
    # 构建样本文本
    samples_text = ""
    for i, sample in enumerate(samples):
        name = sample_names[i] if sample_names and i < len(sample_names) else f"样本{i+1}"
        samples_text += f"\n--- {name} ---\n{sample[:2000]}\n"
    
    system_prompt = """你是一个短视频内容分析专家。你的任务是从样本文案中提炼出风格特征。

【分析维度】
1. **开场风格** (opening_style)
   - 怎么开头？（设问/冲突/数据/故事/悬念）
   - 前3秒怎么抓人？
   - 常用的开场句式

2. **语言风格** (language_style)
   - 口语化程度（非常口语/半口语/书面）
   - 常用词汇和表达
   - 禁忌词汇（避免使用的表达）
   - 口头禅或标志性表达

3. **节奏感** (rhythm)
   - 句子长短变化规律
   - 段落之间的过渡方式
   - 情绪起伏模式（低→高→低/平稳→爆发/持续高涨）

4. **结构模式** (structure)
   - 典型结构（hook→问题→方案→金句/hook→数据→分析→号召等）
   - 场景数量和分配
   - 转场方式

5. **结尾风格** (closing_style)
   - 怎么收尾？（金句/号召/悬念/升华/反转）
   - 常用的结尾句式

6. **情绪特征** (emotional_traits)
   - 整体情绪基调（幽默/严肃/犀利/温暖/激昂）
   - 情绪变化规律
   - 与观众的情感连接方式

7. **视觉节奏** (visual_rhythm)
   - 画面切换频率
   - 文字出现节奏
   - 数据/图表使用频率

【输出格式】
输出JSON对象：
{
  "style_name": "风格名称（自动生成）",
  "description": "风格描述（一句话）",
  "opening_style": {
    "pattern": "开场模式描述",
    "examples": ["示例1", "示例2"],
    "keywords": ["常用开场词"]
  },
  "language_style": {
    "tone": "语气描述",
    "vocabulary_level": "词汇难度（通俗/中等/专业）",
    "signature_phrases": ["标志性表达1", "标志性表达2"],
    "forbidden_phrases": ["禁忌表达1", "禁忌表达2"],
    "oral_level": "口语化程度（1-10）"
  },
  "rhythm": {
    "sentence_pattern": "句子长短规律",
    "transition_style": "过渡方式",
    "emotional_arc": "情绪弧线"
  },
  "structure": {
    "typical_structure": "典型结构描述",
    "scene_count_range": "场景数量范围",
    "scene_distribution": "场景分配规律"
  },
  "closing_style": {
    "pattern": "收尾模式",
    "examples": ["示例1", "示例2"]
  },
  "emotional_traits": {
    "base_emotion": "基础情绪",
    "emotion_variation": "情绪变化规律",
    "audience_connection": "与观众连接方式"
  },
  "visual_rhythm": {
    "cut_frequency": "切换频率（快/中/慢）",
    "text_density": "文字密度",
    "data_usage": "数据使用频率"
  },
  "fusion_guide": "融合建议（如何与其他风格结合）"
}

只输出JSON，不要其他内容。"""

    prompt = f"""以下是从不同来源收集的短视频口播文案样本：

{samples_text}

请分析以上样本的风格特征，提炼出可复用的风格配置。要求：
1. 识别共同的风格特征
2. 提取可复用的模式和句式
3. 标注需要避免的表达
4. 给出融合建议

输出JSON对象。"""

    response = call_llm(prompt, system_prompt, max_tokens=4000)
    
    if not response:
        return {
            "style_name": "默认风格",
            "description": "口语化科技风",
            "error": "LLM返回为空"
        }
    
    # 解析JSON
    try:
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*$', '', cleaned).strip()
        
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result.setdefault("style_name", "学习风格")
            result.setdefault("description", "")
            result.setdefault("source_count", len(samples))
            return result
    except json.JSONDecodeError:
        print(f"  ⚠️ [style-learner] JSON解析失败")
    
    return {
        "style_name": "学习风格",
        "description": "从样本中学习的风格",
        "raw_analysis": response[:500],
        "error": "JSON解析失败"
    }


def merge_styles(base_style: dict, new_style: dict) -> dict:
    """融合两个风格配置"""
    
    system_prompt = """你是一个短视频风格设计专家。你的任务是融合两个风格配置，生成一个新的综合风格。

【融合原则】
1. 保留两个风格的优点
2. 解决冲突时，优先选择更口语化、更有节奏感的表达
3. 标注融合后的特色
4. 给出具体的使用建议

【输出格式】
输出融合后的风格配置JSON（格式与输入相同）。"""

    prompt = f"""基础风格：
{json.dumps(base_style, ensure_ascii=False, indent=2)}

新学习的风格：
{json.dumps(new_style, ensure_ascii=False, indent=2)}

请融合以上两个风格，生成一个新的综合风格。要求：
1. 保留两个风格的优点
2. 优先选择更口语化、更有节奏感的表达
3. 标注融合特色

输出JSON对象。"""

    response = call_llm(prompt, system_prompt, max_tokens=4000)
    
    if not response:
        # 简单合并
        merged = base_style.copy()
        merged["style_name"] = f"{base_style.get('style_name', '')} + {new_style.get('style_name', '')}"
        merged["description"] = f"融合风格：{base_style.get('description', '')} + {new_style.get('description', '')}"
        return merged
    
    # 解析JSON
    try:
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*$', '', cleaned).strip()
        
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    return base_style


def run(context: dict) -> dict:
    """主入口：学习风格"""
    
    print(f"  [style-learner] 开始学习风格...")
    
    load_env()
    
    # 获取样本
    samples = context.get("samples", [])
    sample_names = context.get("sample_names", [])
    
    if not samples:
        print(f"  ❌ [style-learner] 没有提供样本")
        return context
    
    print(f"  [style-learner] 样本数量: {len(samples)}")
    
    # 分析风格
    new_style = analyze_style(samples, sample_names)
    
    # 如果已有基础风格，进行融合
    existing_style = None
    if STYLE_PROFILE_PATH.exists():
        with open(STYLE_PROFILE_PATH, "r", encoding="utf-8") as f:
            existing_style = json.load(f)
        print(f"  [style-learner] 已有基础风格: {existing_style.get('style_name', 'N/A')}")
    
    if existing_style:
        print(f"  [style-learner] 融合风格...")
        final_style = merge_styles(existing_style, new_style)
    else:
        final_style = new_style
    
    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(STYLE_PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(final_style, f, ensure_ascii=False, indent=2)
    
    print(f"  [style-learner] ✅ 风格学习完成")
    print(f"    风格名称: {final_style.get('style_name', 'N/A')}")
    print(f"    风格描述: {final_style.get('description', 'N/A')}")
    print(f"    已保存到: {STYLE_PROFILE_PATH}")
    
    # 更新context
    context["style_profile_path"] = str(STYLE_PROFILE_PATH)
    context["style_profile"] = final_style
    
    return context


if __name__ == "__main__":
    # 测试：分析一个样本
    test_samples = [
        """你以为AI生成的文章、报告都可信吗？2026年，OpenAI用一项新技术改变了游戏规则！
问题已经很明显了。虚假信息、版权模糊、来源不清…AI越强大，我们反而越不敢轻易相信。
OpenAI的答案，叫"内容溯源"。说白了，就是给每一份AI生成的内容，打上一个独一无二、且无法篡改的"出生证明"。
技术可以狂奔，但信任必须有迹可循。2026，我们等待的，正是这样一种，能够被看见的诚实。"""
    ]
    
    test_context = {
        "samples": test_samples,
        "sample_names": ["AI内容溯源文案"]
    }
    result = run(test_context)
    
    print(f"\n✅ 测试完成")
    print(f"  风格名称: {result.get('style_profile', {}).get('style_name', 'N/A')}")
