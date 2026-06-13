"""
topic_selector/impl.py — 选题器（适配v4热点列表格式）
功能：从topic-scout采集的热点列表中，多维度筛选最佳选题

职责边界：
- 读取topic-scout的verified_topics列表
- 多维度评估每个热点（热度、时效性、受众匹配、可行性、差异化、情绪价值）
- 输出选定的话题+角度+来源追踪

输入：output/topic_research.json（topic-scout的verified_topics列表）
输出：output/topic_selected.json（选定的话题+角度+评分+来源URL）
"""

import os
import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from llm_utils import call_llm
from datetime import datetime

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
RESEARCH_PATH = OUTPUT_DIR / "topic_research.json"
SELECTED_PATH = OUTPUT_DIR / "topic_selected.json"

# LLM配置
# LLM配置已移至llm_utils.py


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




def select_topic(research_data: dict) -> dict:
    """从热点列表中多维度筛选最佳选题"""
    
    # 兼容新旧格式
    # 新格式：verified_topics列表
    # 旧格式：单个research report
    verified_topics = research_data.get("verified_topics", [])
    
    if verified_topics:
        # 新格式：从热点列表中选题
        return _select_from_topics_list(verified_topics)
    else:
        # 旧格式：从单个报告中选题
        return _select_from_report(research_data)


def _select_from_topics_list(verified_topics: list) -> dict:
    """从热点列表中选题"""
    
    # 构建热点摘要
    topics_text = ""
    for i, topic in enumerate(verified_topics[:30], 1):
        title = topic.get("title", "")
        sources = topic.get("sources", [])
        source_urls = topic.get("source_urls", [])
        hot_value = topic.get("hot_value", 0)
        verification = topic.get("verification", {})
        confidence = verification.get("confidence", 0)
        cross_checked = verification.get("cross_checked", False)
        
        # 格式化来源
        sources_str = "、".join(sources[:3])
        urls_str = ""
        if source_urls:
            urls_str = f" (URL: {source_urls[0][:50]}...)"
        
        # 交叉验证标记
        cross_mark = "✓交叉验证" if cross_checked else ""
        
        topics_text += f"{i}. [{sources_str}] {title} | 热度:{hot_value} | 置信度:{confidence} {cross_mark}{urls_str}\n"
    
    system_prompt = """你是一个资深的短视频选题专家。你的任务是从热点列表中，筛选出最佳的短视频选题。

【选题评估维度】（每个维度1-10分）
1. **热度** (hot_score): 热度值、讨论度
2. **时效性** (timeliness): 是否是最近24-48小时的热点
3. **受众匹配** (audience_fit): 是否适合短视频受众（18-35岁为主），是否通俗易懂
4. **内容可行性** (content_feasibility): 是否有足够素材做60-90秒视频，是否能讲清楚
5. **差异化** (uniqueness): 是否能做出独特角度，而不是千篇一律的报道
6. **情绪价值** (emotional_value): 是否能引发共鸣/争议/好奇/惊讶

【选题方向】
- 不要选太宏大的话题（如"国际局势"），要选具体的切入点
- 优先选有"冲突感"、"反差感"、"实用价值"的角度
- 优先选交叉验证的热点（多个平台都有，信息更可靠）
- 要能用一句话说清楚"这个视频讲什么"

【来源追踪要求】
- 每个关键点必须标注信息来源
- 如果有URL，必须保留URL
- 后续需要根据这些URL进行截图、录屏、引用

【输出格式】
{
  "selected_topic": "选定的话题（一句话）",
  "angle": "切入角度（具体、有冲突感或实用价值）",
  "hook": "开头hook（前3秒抓住观众的那句话）",
  "scores": {
    "hot_score": 0-10,
    "timeliness": 0-10,
    "audience_fit": 0-10,
    "content_feasibility": 0-10,
    "uniqueness": 0-10,
    "emotional_value": 0-10,
    "total": 0-60
  },
  "reason": "选择这个话题的理由（2-3句话）",
  "target_audience": "目标观众画像（年龄、兴趣、痛点）",
  "key_points": [
    {
      "point": "关键点描述",
      "source": "信息来源（平台/网站名）",
      "source_url": "原始链接（如果有）",
      "data": "支撑数据（如果有）"
    }
  ],
  "reference_sources": [
    {
      "type": "来源类型",
      "platform": "平台名",
      "title": "内容标题",
      "url": "原始链接"
    }
  ],
  "screenshot_targets": [
    {
      "url": "需要截图的URL",
      "description": "截图什么内容",
      "purpose": "用途"
    }
  ],
  "alternative_topics": [
    {"topic": "备选话题1", "angle": "切入角度", "total_score": 0-60}
  ]
}

只输出JSON，不要其他内容。"""

    prompt = f"""当前热点列表（来自多个平台，带来源和置信度）：

{topics_text}

请从以上热点中筛选出最佳的短视频选题。要求：
1. 优先选交叉验证的热点（置信度高）
2. 选题要具体，不能太宏大
3. 要有冲突感或实用价值
4. 要能用一句话说清楚
5. 给出2个备选方案
6. 每个关键点必须标注来源URL
7. 列出需要截图的目标URL

输出JSON对象。"""

    response = call_llm(prompt, system_prompt, max_tokens=4000)
    
    if not response:
        return {
            "selected_topic": "无可用信息",
            "angle": "无法确定",
            "scores": {"total": 0},
            "reason": "LLM返回为空",
            "error": "LLM返回为空"
        }
    
    # 解析JSON
    try:
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*$', '', cleaned).strip()
        
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            
            # 确保必要字段
            result.setdefault("selected_topic", "")
            result.setdefault("angle", "")
            result.setdefault("hook", "")
            result.setdefault("scores", {"total": 30})
            result.setdefault("reason", "")
            result.setdefault("target_audience", "18-35岁年轻网民")
            result.setdefault("key_points", [])
            result.setdefault("reference_sources", [])
            result.setdefault("screenshot_targets", [])
            result.setdefault("alternative_topics", [])
            
            # 计算总分
            scores = result.get("scores", {})
            if "total" not in scores:
                scores["total"] = sum(v for k, v in scores.items() if k != "total" and isinstance(v, (int, float)))
                result["scores"] = scores
            
            return result
    except json.JSONDecodeError:
        print(f"  ⚠️ [topic-selector] JSON解析失败")
    
    return {
        "selected_topic": "无可用信息",
        "angle": "无法确定",
        "scores": {"total": 0},
        "reason": "JSON解析失败",
        "error": "JSON解析失败"
    }


def _select_from_report(research_data: dict) -> dict:
    """从单个报告中选题（兼容旧格式）"""
    
    topic = research_data.get("topic", "")
    summary = research_data.get("summary", "")
    key_facts = research_data.get("key_facts", [])
    key_data = research_data.get("key_data", [])
    trends = research_data.get("trends", [])
    opportunities = research_data.get("opportunities", [])
    sources = research_data.get("sources", [])
    
    # 构建来源摘要
    sources_text = "\n信息来源（带URL）:\n"
    for i, src in enumerate(sources, 1):
        sources_text += f"{i}. {src}\n"
    
    system_prompt = """你是一个资深的短视频选题专家。你的任务是从采集到的信息中，筛选出最佳的短视频选题。

【选题评估维度】（每个维度1-10分）
1. **热度** (hot_score): 各平台热搜排名、搜索量、讨论度
2. **时效性** (timeliness): 信息的新鲜程度，是否是最近24-48小时的热点
3. **受众匹配** (audience_fit): 是否适合短视频受众（18-35岁为主），是否通俗易懂
4. **内容可行性** (content_feasibility): 是否有足够素材做60-90秒视频，是否能讲清楚
5. **差异化** (uniqueness): 是否能做出独特角度，而不是千篇一律的报道
6. **情绪价值** (emotional_value): 是否能引发共鸣/争议/好奇/惊讶

【输出格式】
{
  "selected_topic": "选定的话题（一句话）",
  "angle": "切入角度",
  "hook": "开头hook",
  "scores": {"total": 0-60},
  "reason": "选择理由",
  "target_audience": "目标受众",
  "key_points": [...],
  "reference_sources": [...],
  "screenshot_targets": [...],
  "alternative_topics": [...]
}

只输出JSON，不要其他内容。"""

    prompt = f"""原始话题: {topic}

采集到的信息:
摘要: {summary}

关键事实:
{json.dumps(key_facts, ensure_ascii=False, indent=2)}

关键数据:
{json.dumps(key_data, ensure_ascii=False, indent=2)}

趋势:
{json.dumps(trends, ensure_ascii=False, indent=2)}
{sources_text}

请从以上信息中筛选出最佳的短视频选题。输出JSON对象。"""

    response = call_llm(prompt, system_prompt, max_tokens=4000)
    
    if not response:
        return {
            "selected_topic": topic or "无可用信息",
            "angle": "综合分析",
            "scores": {"total": 0},
            "reason": "LLM返回为空",
            "error": "LLM返回为空"
        }
    
    # 解析JSON
    try:
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*$', '', cleaned).strip()
        
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            
            result.setdefault("selected_topic", topic)
            result.setdefault("angle", "")
            result.setdefault("hook", "")
            result.setdefault("scores", {"total": 30})
            result.setdefault("reason", "")
            result.setdefault("target_audience", "18-35岁年轻网民")
            result.setdefault("key_points", [])
            result.setdefault("reference_sources", [])
            result.setdefault("screenshot_targets", [])
            result.setdefault("alternative_topics", [])
            
            scores = result.get("scores", {})
            if "total" not in scores:
                scores["total"] = sum(v for k, v in scores.items() if k != "total" and isinstance(v, (int, float)))
                result["scores"] = scores
            
            return result
    except json.JSONDecodeError:
        pass
    
    return {
        "selected_topic": topic or "无可用信息",
        "angle": "综合分析",
        "scores": {"total": 0},
        "reason": "JSON解析失败",
        "error": "JSON解析失败"
    }


def run(context: dict) -> dict:
    """主入口：选题"""
    
    print(f"  [topic-selector] 开始选题...")
    
    
    # 读取research数据
    research_path = context.get("research_path") or str(RESEARCH_PATH)
    if not os.path.exists(research_path):
        print(f"  ❌ [topic-selector] 找不到研究数据: {research_path}")
        return context
    
    with open(research_path, "r", encoding="utf-8") as f:
        research_data = json.load(f)
    
    # 显示数据概况
    verified_topics = research_data.get("verified_topics", [])
    if verified_topics:
        print(f"  [topic-selector] 热点列表: {len(verified_topics)} 个热点")
        cross_checked = len([t for t in verified_topics if t.get("verification", {}).get("cross_checked")])
        print(f"  [topic-selector] 交叉验证: {cross_checked} 个")
    else:
        print(f"  [topic-selector] 原始话题: {research_data.get('topic', 'N/A')}")
    
    # 选题
    selected = select_topic(research_data)
    # 兼容：确保 topic 字段存在（下游 skill 读 topic，不读 selected_topic）
    if selected.get("selected_topic") and not selected.get("topic"):
        selected["topic"] = selected["selected_topic"]
    
    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SELECTED_PATH, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)
    
    print(f"  [topic-selector] ✅ 选题完成")
    print(f"    选定话题: {selected.get('selected_topic', 'N/A')}")
    print(f"    切入角度: {selected.get('angle', 'N/A')}")
    print(f"    总分: {selected.get('scores', {}).get('total', 'N/A')}/60")
    print(f"    关键点: {len(selected.get('key_points', []))} 个")
    print(f"    来源: {len(selected.get('reference_sources', []))} 个")
    print(f"    截图目标: {len(selected.get('screenshot_targets', []))} 个")
    print(f"    已保存到: {SELECTED_PATH}")
    
    # 更新context
    context["topic_selected_path"] = str(SELECTED_PATH)
    context["topic_selected"] = selected
    context["selected_topic"] = selected.get("selected_topic", "")
    context["selected_angle"] = selected.get("angle", "")
    
    return context


if __name__ == "__main__":
    test_context = {}
    result = run(test_context)
    
    print(f"\n✅ 测试完成")
    print(f"  选定话题: {result.get('selected_topic', 'N/A')}")
    print(f"  切入角度: {result.get('selected_angle', 'N/A')}")
