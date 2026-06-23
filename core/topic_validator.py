"""
core/topic_validator.py — 选题结构验证
优先选择有天然结构的选题
"""

import re
import logging

logger = logging.getLogger(__name__)


# 有天然结构的关键词
STRUCTURED_KEYWORDS = [
    "三个", "三盏", "三重", "三维", "三方",
    "双重", "双面", "双向",
    "四个", "四重",
    "五大", "五维",
    "消费", "投资", "债务",  # 经济三段
    "红灯", "预警", "信号",
    "对比", "对比", "VS",
]

# 开放式问题（质量差）
OPEN_KEYWORDS = [
    "如何看待", "怎样看待", "怎么看待",
    "未来趋势", "发展趋势", "发展方向",
    "有什么影响", "会产生什么",
    "意味着什么", "说明了什么",
]


def check_topic_structure(topic: str) -> dict:
    """检查选题是否有天然结构
    
    返回:
        {
            "has_structure": bool,  # 是否有结构
            "is_open": bool,        # 是否开放式问题
            "score": float,         # 结构评分 0-1
            "reason": str,          # 原因
        }
    """
    if not topic:
        return {
            "has_structure": False,
            "is_open": True,
            "score": 0.0,
            "reason": "空选题"
        }
    
    # 检查是否有结构关键词
    has_structure = any(kw in topic for kw in STRUCTURED_KEYWORDS)
    
    # 检查是否是开放式问题
    is_open = any(kw in topic for kw in OPEN_KEYWORDS)
    
    # 计算评分
    if has_structure and not is_open:
        score = 0.9
        reason = "有天然结构"
    elif has_structure and is_open:
        score = 0.6
        reason = "有结构但偏开放"
    elif not has_structure and not is_open:
        score = 0.5
        reason = "无明显结构"
    else:
        score = 0.3
        reason = "开放式问题"
    
    # 检查是否有具体数据
    has_numbers = bool(re.search(r'\d+', topic))
    if has_numbers:
        score += 0.1
    
    return {
        "has_structure": has_structure,
        "is_open": is_open,
        "score": min(score, 1.0),
        "reason": reason,
    }


def validate_topic(topic: str, min_score: float = 0.5) -> tuple:
    """验证选题是否合格
    
    返回:
        (is_valid, result_dict)
    """
    result = check_topic_structure(topic)
    is_valid = result["score"] >= min_score
    
    if not is_valid:
        logger.warning(f"选题不合格: {topic} (score={result['score']}, reason={result['reason']})")
    
    return is_valid, result
