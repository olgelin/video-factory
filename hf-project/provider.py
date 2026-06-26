#!/usr/bin/env python3
"""
provider.py — LLM Provider 抽象层

从 OpenMontage 借鉴的 provider 模式：
- 自动发现可用 provider（从 config + 环境变量）
- 按任务类型（research/selection/creative）智能路由
- 7 维度评分选择最优 provider
- 内置 429 重试 + 限流保护

用法:
    from provider import ProviderRegistry
    registry = ProviderRegistry()
    result = registry.call("creative", prompt, system_prompt)
"""

import os
import re
import json
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional

import requests
import yaml


# ============================================================
# Provider Score
# ============================================================

@dataclass
class ProviderScore:
    """Provider 评分"""
    name: str
    model: str
    task_fit: float = 0.0       # 任务匹配度 30%
    output_quality: float = 0.0  # 输出质量 20%
    reliability: float = 0.0     # 可靠性 15%
    cost_efficiency: float = 0.0 # 性价比 10%
    latency: float = 0.0         # 延迟 5%
    control: float = 0.0         # 可控性 15%
    continuity: float = 0.0      # 连续性 5%

    @property
    def weighted_score(self) -> float:
        return (
            self.task_fit * 0.30
            + self.output_quality * 0.20
            + self.control * 0.15
            + self.reliability * 0.15
            + self.cost_efficiency * 0.10
            + self.latency * 0.05
            + self.continuity * 0.05
        )


# ============================================================
# Provider Registry
# ============================================================

# 任务类型 → 推荐模型特征
TASK_PROFILES = {
    "research": {
        "description": "信息采集、热点分析",
        "prefer": ["fast", "cheap"],
        "min_quality": 0.5,
        "max_tokens": 4000,
    },
    "selection": {
        "description": "选题评估、多维度打分",
        "prefer": ["balanced"],
        "min_quality": 0.6,
        "max_tokens": 4000,
    },
    "creative": {
        "description": "脚本创作、HTML生成、设计系统",
        "prefer": ["quality", "creative"],
        "min_quality": 0.7,
        "max_tokens": 12000,
    },
    "analysis": {
        "description": "质量诊断、内容审核",
        "prefer": ["fast", "accurate"],
        "min_quality": 0.5,
        "max_tokens": 4000,
    },
}


class ProviderRegistry:
    """LLM Provider 注册与路由"""

    def __init__(self, config_path: str = None):
        self._providers: list[dict] = []
        self._rate_limiter = RateLimiter()
        self._load_config(config_path)
        self._discover()

    def _load_config(self, config_path: str = None):
        """加载配置"""
        # 1. 尝试从 Hermes config.yaml
        if config_path is None:
            hermes_home = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
            config_path = hermes_home / "config.yaml"

        self._config = {}
        if Path(config_path).exists():
            try:
                with open(config_path) as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception:
                pass

        # 2. 环境变量覆盖
        self._api_key = (
            os.environ.get("VF_API_KEY")
            or os.environ.get("VOLC_API_KEY")
            or self._config.get("model", {}).get("api_key", "")
        )
        self._base_url = (
            os.environ.get("VF_BASE_URL")
            or self._config.get("model", {}).get("base_url", "")
            or "https://ark.cn-beijing.volces.com/api/plan/v3"
        )

    def _discover(self):
        """自动发现可用 provider"""
        if not self._api_key:
            return

        # 主模型（从 config 读取）
        default_models = self._config.get("model", {}).get("default", "")
        if default_models:
            for model_name in default_models.split(","):
                model_name = model_name.strip()
                if model_name:
                    self._providers.append({
                        "name": model_name,
                        "model": model_name,
                        "url": self._base_url.rstrip("/") + "/chat/completions",
                        "api_key": self._api_key,
                        "quality": self._estimate_quality(model_name),
                        "speed": self._estimate_speed(model_name),
                        "cost": self._estimate_cost(model_name),
                    })

        # 辅助模型（从 config 读取）
        for aux_name in ["approval", "title_generation", "vision"]:
            aux_cfg = self._config.get("auxiliary", {}).get(aux_name, {})
            aux_model = aux_cfg.get("model", "")
            aux_key = aux_cfg.get("api_key", "")
            aux_url = aux_cfg.get("base_url", "")
            if aux_model and aux_key and aux_url:
                # 避免重复
                if not any(p["model"] == aux_model for p in self._providers):
                    self._providers.append({
                        "name": f"aux-{aux_name}",
                        "model": aux_model,
                        "url": aux_url.rstrip("/") + "/chat/completions",
                        "api_key": aux_key,
                        "quality": self._estimate_quality(aux_model),
                        "speed": self._estimate_speed(aux_model),
                        "cost": self._estimate_cost(aux_model),
                    })

    def _estimate_quality(self, model: str) -> float:
        """估算模型质量"""
        if "pro" in model.lower() or "k2" in model.lower():
            return 0.9
        if "flash" in model.lower():
            return 0.7
        if "glm" in model.lower():
            return 0.75
        if "minimax" in model.lower():
            return 0.7
        return 0.6

    def _estimate_speed(self, model: str) -> float:
        """估算模型速度"""
        if "flash" in model.lower():
            return 0.9
        if "minimax" in model.lower():
            return 0.8
        if "glm" in model.lower():
            return 0.7
        if "pro" in model.lower() or "k2" in model.lower():
            return 0.5
        return 0.6

    def _estimate_cost(self, model: str) -> float:
        """估算成本（越低越好 → 分数越高）"""
        if "flash" in model.lower():
            return 0.9
        if "minimax" in model.lower():
            return 0.8
        if "glm" in model.lower():
            return 0.7
        if "pro" in model.lower():
            return 0.4
        if "k2" in model.lower():
            return 0.3
        return 0.5

    def score_providers(self, task: str) -> list[ProviderScore]:
        """为指定任务评分所有 provider"""
        profile = TASK_PROFILES.get(task, TASK_PROFILES["creative"])
        scores = []

        for p in self._providers:
            s = ProviderScore(
                name=p["name"],
                model=p["model"],
                task_fit=self._calc_task_fit(p, profile),
                output_quality=p["quality"],
                reliability=0.8,
                cost_efficiency=p["cost"],
                latency=p["speed"],
                control=0.7,
                continuity=0.8,
            )
            if s.output_quality >= profile["min_quality"]:
                scores.append(s)

        scores.sort(key=lambda x: x.weighted_score, reverse=True)
        return scores

    def _calc_task_fit(self, provider: dict, profile: dict) -> float:
        """计算任务匹配度"""
        score = 0.5
        prefers = profile.get("prefer", [])
        if "quality" in prefers and provider["quality"] > 0.8:
            score += 0.3
        if "fast" in prefers and provider["speed"] > 0.7:
            score += 0.3
        if "cheap" in prefers and provider["cost"] > 0.7:
            score += 0.3
        if "creative" in prefers and provider["quality"] > 0.7:
            score += 0.2
        return min(score, 1.0)

    def call(
        self,
        task: str,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = None,
        timeout: int = 300,
    ) -> str:
        """
        智能路由 LLM 调用

        Args:
            task: 任务类型 (research/selection/creative/analysis)
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大 token 数
            timeout: 超时时间

        Returns:
            LLM 响应文本
        """
        if max_tokens is None:
            max_tokens = TASK_PROFILES.get(task, {}).get("max_tokens", 4000)

        scores = self.score_providers(task)
        if not scores:
            raise RuntimeError("没有可用的 LLM provider")

        print(f"  [Provider] 任务: {task}, 候选: {len(scores)} 个")

        for score in scores:
            provider = next(
                (p for p in self._providers if p["model"] == score.model), None
            )
            if not provider:
                continue

            # 限流检查
            if not self._rate_limiter.acquire(provider["model"]):
                print(f"  [Provider] {score.model} 被限流，跳过")
                continue

            print(f"  [Provider] 选择 {score.model} (score={score.weighted_score:.2f})")

            result = self._call_single(
                provider, prompt, system_prompt, max_tokens, timeout
            )
            if result:
                return result

            print(f"  [Provider] {score.model} 失败，尝试下一个...")

        raise RuntimeError("所有 LLM provider 均调用失败")

    def _call_single(
        self,
        provider: dict,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        timeout: int,
    ) -> Optional[str]:
        """调用单个 provider（带重试）"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": provider["model"],
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }

        for retry in range(3):
            try:
                resp = requests.post(
                    provider["url"],
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )

                if resp.status_code == 429:
                    wait = (retry + 1) * 5
                    print(f"  [Provider] {provider['name']} 429, 等待 {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code == 200:
                    data = resp.json()
                    msg = data.get("choices", [{}])[0].get("message", {})
                    content = msg.get("content", "").strip()

                    # 处理 thinking 标签
                    content = re.sub(r"^.+? response\s*", "", content, flags=re.DOTALL).strip()
                    if content:
                        return content

                    # 从 reasoning_content 提取
                    reasoning = msg.get("reasoning_content", "").strip()
                    if reasoning:
                        return reasoning

                    return content

                print(f"  [Provider] {provider['name']} HTTP {resp.status_code}")
                if retry < 2:
                    time.sleep((retry + 1) * 2)

            except requests.Timeout:
                print(f"  [Provider] {provider['name']} 超时")
                if retry < 2:
                    time.sleep((retry + 1) * 3)
            except Exception as e:
                print(f"  [Provider] {provider['name']} 错误: {e}")
                if retry < 2:
                    time.sleep((retry + 1) * 2)

        return None

    @property
    def available_models(self) -> list[str]:
        return [p["model"] for p in self._providers]

    def support_envelope(self) -> dict:
        """能力清单"""
        return {
            "providers": len(self._providers),
            "models": self.available_models,
            "tasks": list(TASK_PROFILES.keys()),
        }


class RateLimiter:
    """简单的令牌桶限流器"""

    def __init__(self, max_calls: int = 10, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def acquire(self, key: str) -> bool:
        """尝试获取令牌"""
        now = time.time()
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = []
            # 清理过期记录
            self._buckets[key] = [
                t for t in self._buckets[key] if now - t < self.period
            ]
            if len(self._buckets[key]) >= self.max_calls:
                return False
            self._buckets[key].append(now)
            return True


# ============================================================
# 便捷函数（兼容旧 llm_utils 接口）
# ============================================================

_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


def call_llm(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 4000,
    timeout: int = 300,
    task: str = "creative",
) -> str:
    """便捷 LLM 调用（兼容旧接口）"""
    return get_registry().call(task, prompt, system_prompt, max_tokens, timeout)
