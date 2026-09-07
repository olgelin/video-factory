"""
core/topic_validator.py — 选题结构验证
优先选择有天然结构、有信息差、有内涵的选题，过滤介绍型浅薄话题。
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

# 🔴 介绍型关键词（浅薄，百科式，low）
# 用户 2026-09-06 纠正："介绍曲阳xxx"太 low —— 好话题是"揭盖子"不是"翻资料"
INTRO_KEYWORDS = [
    "介绍", "科普", "了解一下", "认识一下", "是什么", "有哪些",
    "简介", "概述", "带你了解", "带你认识", "走进", "探访",
]

# 🔴 信息差/争议关键词（有内涵，揭盖子）
INSIGHT_KEYWORDS = [
    "真相", "背后", "内幕", "揭穿", "骗局", "陷阱", "争议", "质疑",
    "翻车", "打脸", "隐藏", "不为人知", "秘密", "谎言", "收割", "套路",
    "为什么", "凭什么", "靠的是", "其实是", "竟然是", "居然",
    "钞能力", "猫腻", "玄机", "暗箱", "潜规则", "黑幕",
    "落马", "暴雷", "爆雷", "崩盘", "跑路", "血亏",
]


def check_topic_structure(topic: str) -> dict:
    """检查选题是否有天然结构、信息差、内涵

    返回:
        {
            "has_structure": bool,  # 是否有结构
            "is_open": bool,        # 是否开放式问题
            "is_intro": bool,       # 是否介绍型（浅薄）
            "has_insight": bool,    # 是否有信息差/争议
            "score": float,         # 综合评分 0-1
            "reason": str,          # 原因
        }
    """
    if not topic:
        return {
            "has_structure": False,
            "is_open": True,
            "is_intro": False,
            "has_insight": False,
            "score": 0.0,
            "reason": "空选题"
        }

    # 检查结构/开放/介绍/信息差
    has_structure = any(kw in topic for kw in STRUCTURED_KEYWORDS)
    is_open = any(kw in topic for kw in OPEN_KEYWORDS)
    is_intro = any(kw in topic for kw in INTRO_KEYWORDS)
    has_insight = any(kw in topic for kw in INSIGHT_KEYWORDS)

    # 基础分（结构 + 开放度）
    if has_structure and not is_open:
        score = 0.9
        base_reason = "有天然结构"
    elif has_structure and is_open:
        score = 0.6
        base_reason = "有结构但偏开放"
    elif not has_structure and not is_open:
        score = 0.5
        base_reason = "无明显结构"
    else:
        score = 0.3
        base_reason = "开放式问题"

    reasons = [base_reason]

    # 有数据加分
    has_numbers = bool(re.search(r'\d+', topic))
    if has_numbers:
        score += 0.1
        reasons.append("有数据")

    # 信息差/争议加分（有内涵）
    if has_insight:
        score += 0.15
        reasons.append("有信息差/争议")

    # 介绍型扣分（浅薄）
    if is_intro:
        score -= 0.4
        reasons.append("介绍型(浅薄)")

    score = max(0.0, min(1.0, score))

    return {
        "has_structure": has_structure,
        "is_open": is_open,
        "is_intro": is_intro,
        "has_insight": has_insight,
        "score": score,
        "reason": "、".join(reasons),
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
