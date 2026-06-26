"""
llm_utils.py - 通用LLM调用工具（v5 — 委托给 provider.py）

向后兼容层：所有现有 skill 无需修改 import，底层已切换至 Provider 抽象。
新增功能：
- 智能 provider 路由（按任务类型选最优模型）
- 7 维度评分
- 令牌桶限流
- 成本追踪

如需直接使用新接口：
    from provider import ProviderRegistry, call_llm as call_llm_v5
"""

import os
import sys
from pathlib import Path

# 确保 provider.py 可导入
_provider_dir = Path(__file__).parent
if str(_provider_dir) not in sys.path:
    sys.path.insert(0, str(_provider_dir))

from provider import call_llm as _provider_call_llm, get_registry


# ============================================================
# 向后兼容接口
# ============================================================

def call_llm(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 4000,
    timeout: int = 300,
    task: str = "creative",
) -> str:
    """
    通用LLM调用（兼容旧接口，底层使用 provider.py）

    Args:
        prompt: 用户提示
        system_prompt: 系统提示
        max_tokens: 最大 token 数
        timeout: 超时时间
        task: 任务类型 (research/selection/creative/analysis)

    Returns:
        LLM 响应文本
    """
    return _provider_call_llm(prompt, system_prompt, max_tokens, timeout, task)


def call_llm_batch(
    items: list,
    process_fn: callable,
    batch_size: int = 10,
    system_prompt: str = "",
    max_tokens: int = 4000,
) -> list:
    """
    分批处理大量 items

    当 items 数量超过 batch_size 时，分批调用 LLM，然后合并结果。
    """
    if len(items) <= batch_size:
        return process_fn(items, 0)

    print(f"  [LLM Batch] {len(items)} items, batch_size={batch_size}, "
          f"batches={len(items)//batch_size + 1}")

    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        batch_idx = i // batch_size
        print(f"  [LLM Batch] Processing batch {batch_idx+1}/"
              f"{len(items)//batch_size + 1} ({len(batch)} items)")

        batch_results = process_fn(batch, batch_idx)
        if batch_results:
            results.extend(batch_results)
        else:
            print(f"  [LLM Batch] Batch {batch_idx+1} failed, skipping")

    print(f"  [LLM Batch] Total results: {len(results)}")
    return results


# 保留旧接口兼容性
def call_single_llm(prompt, system_prompt="", config=None, max_tokens=4000, timeout=300):
    """调用单个 LLM（兼容旧接口，委托给 provider）"""
    return _provider_call_llm(prompt, system_prompt, max_tokens, timeout)


def load_env():
    """加载环境变量（provider.py 自动处理）"""
    pass


# 敏感词映射（保留兼容）
SENSITIVE_WORD_MAP = {
    "高考": "重要考试", "高考结束": "考试结束", "考场": "考试现场",
    "考生": "学生", "状元": "优秀学生", "分数": "成绩",
    "落榜": "未录取", "作弊": "违规行为", "枪手": "代考者",
    "彩礼": "婚嫁费用", "嫁妆": "婚嫁礼物", "离婚": "婚姻解除",
    "出轨": "婚姻问题", "家暴": "家庭冲突", "色情": "成人内容",
    "赌博": "博彩活动", "毒品": "违禁物品", "枪支": "武器",
    "暴力": "冲突", "自杀": "自我伤害", "抑郁": "心理问题",
    "癌症": "重大疾病", "死亡": "生命终结", "杀人": "致命伤害",
    "强奸": "性侵", "卖淫": "性交易", "嫖娼": "性交易",
    "腐败": "不当行为", "贪污": "资金挪用", "诈骗": "欺诈行为",
    "传销": "非法营销", "邪教": "非法组织", "恐怖": "极端行为",
    "极端": "激进", "分裂": "分离", "颠覆": "推翻",
    "暴动": "骚乱", "起义": "反抗", "革命": "变革", "政变": "权力更迭",
}

# 旧 LLM_CONFIGS（保留兼容，但不再使用）
LLM_CONFIGS = []
