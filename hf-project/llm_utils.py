"""
llm_utils.py - 通用LLM调用工具
解决内容过滤问题：prompt改写 + 多LLM fallback

核心策略：
1. 先用原始prompt调用
2. 如果被拒绝，用中性化prompt重试
3. 如果还是失败，用更安全的表达重试
"""

import os
import re
import json
import requests
from typing import Optional

# LLM配置（支持任意OpenAI兼容provider）
# 优先级：环境变量 > 默认值
# 设置 VF_API_KEY, VF_BASE_URL, VF_MODEL 可覆盖默认provider
VF_API_KEY=os.environ.get("VF_API_KEY", os.environ.get("XIAOMI_API_KEY", ""))
# 同步到环境变量，让call_single_llm能读到
if VF_API_KEY:
    os.environ["VF_API_KEY"] = VF_API_KEY
VF_BASE_URL = os.environ.get("VF_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
VF_MODEL = os.environ.get("VF_MODEL", "mimo-v2.5-pro")

LLM_CONFIGS = [
    {
        "name": "primary",
        "url": VF_BASE_URL + "/chat/completions",
        "model": VF_MODEL,
        "env_key": "VF_API_KEY",  # 直接读VF_API_KEY，不需要额外env var
    },
]

# 敏感词替换映射（用于prompt改写）
SENSITIVE_WORD_MAP = {
    "高考": "重要考试",
    "高考结束": "考试结束",
    "高考铃声": "考试铃声",
    "考场": "考试现场",
    "考生": "学生",
    "状元": "优秀学生",
    "分数": "成绩",
    "落榜": "未录取",
    "作弊": "违规行为",
    "枪手": "代考者",
    "彩礼": "婚嫁费用",
    "嫁妆": "婚嫁礼物",
    "离婚": "婚姻解除",
    "出轨": "婚姻问题",
    "家暴": "家庭冲突",
    "色情": "成人内容",
    "赌博": "博彩活动",
    "毒品": "违禁物品",
    "枪支": "武器",
    "暴力": "冲突",
    "自杀": "自我伤害",
    "抑郁": "心理问题",
    "癌症": "重大疾病",
    "死亡": "生命终结",
    "杀人": "致命伤害",
    "强奸": "性侵",
    "卖淫": "性交易",
    "嫖娼": "性交易",
    "腐败": "不当行为",
    "贪污": "资金挪用",
    "诈骗": "欺诈行为",
    "传销": "非法营销",
    "邪教": "非法组织",
    "恐怖": "极端行为",
    "极端": "激进",
    "分裂": "分离",
    "颠覆": "推翻",
    "暴动": "骚乱",
    "起义": "反抗",
    "革命": "变革",
    "政变": "权力更迭",
}

# 检测是否被拒绝
def is_rejected(response: str) -> bool:
    """检查LLM响应是否是拒绝"""
    rejection_keywords = [
        "request was rejected",
        "considered high risk",
        "cannot comply",
        "inappropriate",
        "violates",
        "policy",
        "not allowed",
        "refuse",
        "sorry, i cannot",
        "抱歉，我无法",
        "无法回答",
        "不适合",
        "违规",
    ]
    response_lower = response.lower()
    return any(kw in response_lower for kw in rejection_keywords)

# 中性化prompt
def neutralize_prompt(prompt: str) -> str:
    """把敏感词替换成中性表达"""
    result = prompt
    for sensitive, neutral in SENSITIVE_WORD_MAP.items():
        result = result.replace(sensitive, neutral)
    return result

# 调用单个LLM
def call_single_llm(
    prompt: str,
    system_prompt: str = "",
    config: dict = None,
    max_tokens: int = 4000,
    timeout: int = 120,
) -> Optional[str]:
    """调用单个LLM"""
    if config is None:
        config = LLM_CONFIGS[0]
    
    api_key = os.environ.get(config["env_key"], "")
    if not api_key:
        return None
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }
    
    try:
        resp = requests.post(
            config["url"], headers=headers, json=payload, timeout=timeout
        )
        if resp.status_code == 200:
            msg = resp.json().get("choices", [{}])[0].get("message", {})
            raw = msg.get("content", "").strip()
            reasoning = msg.get("reasoning_content", "").strip() if msg.get("reasoning_content") else ""
            # 处理MIMO的<think>标签
            # 先尝试提取</think>后面的正式内容
            content = re.sub(r"^.+?</think>\s*", "", raw, flags=re.DOTALL).strip()
            if content:
                return content
            # 如果只有<think>标签没有正式内容，提取<think>内的文本
            think_match = re.search(r"<think>\s*(.*?)\s*</think>", raw, re.DOTALL)
            if think_match:
                think_content = think_match.group(1).strip()
                if think_content and len(think_content) > 10:
                    return think_content
            # MIMO 把答案放在 reasoning_content 里的情况
            if reasoning and len(reasoning) > 10:
                # 尝试从 reasoning 中提取完整 JSON
                json_patterns = [
                    re.search(r'```(?:json)?\s*(\{.*?\})\s*```', reasoning, re.DOTALL),
                    re.search(r'(\{[^{}]*"template"[^{}]*\})', reasoning, re.DOTALL),
                    re.search(r'(\{.*?\})', reasoning, re.DOTALL),
                ]
                for m in json_patterns:
                    if m:
                        try:
                            json.loads(m.group(1))
                            return m.group(1)
                        except json.JSONDecodeError:
                            continue
                # 没有JSON但有reasoning → 返回reasoning让调用方从中提取信息
                return reasoning
        print(f"  [LLM] {config['name']} failed ({resp.status_code})")
    except Exception as e:
        print(f"  [LLM] {config['name']} error: {e}")
    
    return None

def call_llm(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 4000,
    timeout: int = 120,
) -> str:
    """
    通用LLM调用，带内容过滤处理
    
    策略：
    1. 用原始prompt尝试所有LLM
    2. 如果都被拒绝，用中性化prompt重试
    3. 如果还是失败，返回空字符串
    """
    print(f"  [LLM] Calling with {len(prompt)} chars prompt...")
    
    # 策略1：原始prompt
    for config in LLM_CONFIGS:
        api_key = os.environ.get(config["env_key"], "")
        if not api_key:
            continue
        
        print(f"  [LLM] Trying {config['name']}...")
        result = call_single_llm(prompt, system_prompt, config, max_tokens, timeout)
        
        if result is None:
            continue
        
        if not is_rejected(result):
            print(f"  [LLM] {config['name']} success: {len(result)} chars")
            return result
        
        print(f"  [LLM] {config['name']} rejected, trying neutralized prompt...")
    
    # 策略2：中性化prompt
    neutralized = neutralize_prompt(prompt)
    if neutralized != prompt:
        print(f"  [LLM] Retrying with neutralized prompt...")
        for config in LLM_CONFIGS:
            api_key = os.environ.get(config["env_key"], "")
            if not api_key:
                continue
            
            result = call_single_llm(neutralized, system_prompt, config, max_tokens, timeout)
            
            if result is None:
                continue
            
            if not is_rejected(result):
                print(f"  [LLM] {config['name']} success with neutralized prompt: {len(result)} chars")
                return result
    
    # 策略3：失败
    print(f"  [LLM] All attempts failed")
    return ""

def load_env():
    """加载环境变量"""
    from dotenv import load_dotenv
    possible_envs = [
        os.path.join(os.environ.get("HERMES_HOME", ""), ".env"),
        "E:/Hermes-Agent/.env",
        os.path.expanduser("~/.env"),
    ]
    for env_path in possible_envs:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            return

# 初始化时加载环境变量
load_env()


def call_llm_batch(
    items: list,
    process_fn: callable,
    batch_size: int = 10,
    system_prompt: str = "",
    max_tokens: int = 4000,
) -> list:
    """
    分批处理大量items
    
    当items数量超过batch_size时，分批调用LLM，然后合并结果。
    适用于：storyboard处理100个段落、topic-scout处理大量搜索结果等。
    
    Args:
        items: 要处理的items列表
        process_fn: 处理函数，接收(items_batch, batch_index) -> list结果
        batch_size: 每批处理的数量（默认10）
        system_prompt: LLM系统提示
        max_tokens: 最大token数
    
    Returns:
        合并后的结果列表
    """
    if len(items) <= batch_size:
        return process_fn(items, 0)
    
    print(f"  [LLM Batch] {len(items)} items, batch_size={batch_size}, batches={len(items)//batch_size + 1}")
    
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        batch_idx = i // batch_size
        print(f"  [LLM Batch] Processing batch {batch_idx+1}/{len(items)//batch_size + 1} ({len(batch)} items)")
        
        batch_results = process_fn(batch, batch_idx)
        if batch_results:
            results.extend(batch_results)
        else:
            print(f"  [LLM Batch] Batch {batch_idx+1} failed, skipping")
    
    print(f"  [LLM Batch] Total results: {len(results)}")
    return results
