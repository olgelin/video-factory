#!/usr/bin/env python3
"""
provider.py — LLM Provider 抽象层 v2

核心改进：
- 账号级限流（所有模型共享火山引擎账号配额）
- 429 全局退避（一个模型 429，全部暂停等待）
- 按任务智能分配模型（轻任务用便宜模型，重任务用强模型）
- 模型轮换（避免单个模型过热触发限流）

用法:
    from provider import ProviderRegistry
    registry = ProviderRegistry()
    result = registry.call("creative", prompt, system_prompt)
"""

import os
import re
import time
import threading
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional

import requests
import yaml


# ============================================================
# 任务 → 模型分配策略
# ============================================================

# V5.3 模型智能路由：按任务复杂度分配模型
# 原则：轻任务用快模型（flash/glm），重任务用强模型（pro/kimi）
# hf_builder 并行模式：5 模型轮换，避免排队等 pro
TASK_MODEL_MAP = {
    "research": {
        "description": "信息采集、热点分析",
        "primary": "deepseek-v4-flash",  # V5.3: 轻任务，flash 完全够
        "fallback": ["glm-5.2", "minimax-m3"],
        "max_tokens": 4000,
    },
    "selection": {
        "description": "选题评估、多维度打分",
        "primary": "glm-5.2",  # V5.3: 结构化评分，glm 擅长
        "fallback": ["deepseek-v4-flash", "minimax-m3"],
        "max_tokens": 4000,
    },
    "creative": {
        "description": "脚本创作、设计系统、分镜",
        "primary": "deepseek-v4-pro",
        "fallback": ["kimi-k2.7-code", "glm-5.2", "deepseek-v4-flash"],
        "max_tokens": 12000,
        "timeout": 600,
    },
    "creative_light": {
        "description": "歌词、设计系统等轻创意任务（并行时不抢pro）",
        "primary": "kimi-k2.7-code",
        "fallback": ["glm-5.2", "deepseek-v4-flash"],
        "max_tokens": 8000,
        "timeout": 300,
    },
    "creative_html": {
        "description": "hf_builder 场景 HTML 生成（并行模式）",
        "primary": "deepseek-v4-pro",
        "fallback": ["kimi-k2.7-code", "glm-5.2", "deepseek-v4-flash", "minimax-m3"],
        "max_tokens": 12000,
        "timeout": 600,
    },
    "analysis": {
        "description": "质量诊断、内容审核",
        "primary": "deepseek-v4-flash",  # V5.3: 轻任务
        "fallback": ["glm-5.2", "minimax-m3"],
        "max_tokens": 4000,
    },
}

# V5.3: hf_builder 并行模型轮换列表（按场景 index 取模分配）
HF_PARALLEL_MODELS = [
    "deepseek-v4-pro",
    "kimi-k2.7-code",
    "glm-5.2",
    "deepseek-v4-flash",
    "minimax-m3",
]


# ============================================================
# 账号级限流器
# ============================================================

class AccountRateLimiter:
    """账号级令牌桶 — 所有模型共享配额"""

    def __init__(self, max_rpm: int = 100):
        """
        Args:
            max_rpm: 每分钟最大请求数（V5.2 Fix D: 30→100，实际套餐≥500 RPM）
        """
        self.max_rpm = max_rpm
        self.period = 60.0
        self._timestamps: list[float] = []
        self._lock = threading.Lock()
        self._global_cooldown_until: float = 0  # 全局冷却截止时间

    def acquire(self) -> bool:
        """尝试获取令牌，返回是否成功"""
        now = time.time()

        # 全局冷却中
        if now < self._global_cooldown_until:
            remaining = self._global_cooldown_until - now
            if remaining > 0.5:
                return False

        with self._lock:
            # 清理过期
            self._timestamps = [t for t in self._timestamps if now - t < self.period]
            if len(self._timestamps) >= self.max_rpm:
                return False
            self._timestamps.append(now)
            return True

    def report_429(self):
        """收到 429，触发全局冷却"""
        with self._lock:
            # 指数退避：每次 429 冷却时间翻倍，上限 120s
            current_cooldown = max(10, (self._global_cooldown_until - time.time()) * 2)
            self._global_cooldown_until = time.time() + min(current_cooldown, 120)
            print(f"  [RateLimit] 429 触发全局冷却 {min(current_cooldown, 120):.0f}s")

    def wait_if_needed(self):
        """如果需要冷却，阻塞等待"""
        now = time.time()
        if now < self._global_cooldown_until:
            wait = self._global_cooldown_until - now
            if wait > 0:
                print(f"  [RateLimit] 冷却中，等待 {wait:.1f}s...")
                time.sleep(wait)

    @property
    def current_rpm(self) -> int:
        now = time.time()
        with self._lock:
            return len([t for t in self._timestamps if now - t < self.period])


# ============================================================
# Provider Registry
# ============================================================

class ProviderRegistry:
    """LLM Provider 注册与路由"""

    def __init__(self, config_path: str = None):
        self._providers: dict[str, dict] = {}  # model_name → config
        # V5.3.2 Fix: 20 RPM，避免触发火山引擎账号级限流
        max_rpm = int(os.environ.get("VF_MAX_RPM", "20"))
        self._rate_limiter = AccountRateLimiter(max_rpm=max_rpm)
        self._model_429_count: dict[str, int] = {}  # 每个模型的 429 计数
        self._last_model_used: str = ""  # V5.2 Fix C: 记录最后使用的模型名
        self._load_config(config_path)
        self._discover()

    def _load_config(self, config_path: str = None):
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
        if not self._api_key:
            return

        # 从 config 读取所有可用模型
        default_models = self._config.get("model", {}).get("default", "")
        if default_models:
            for model_name in default_models.split(","):
                model_name = model_name.strip()
                if model_name and model_name not in self._providers:
                    self._providers[model_name] = {
                        "model": model_name,
                        "url": self._base_url.rstrip("/") + "/chat/completions",
                        "api_key": self._api_key,
                    }

        # 辅助模型
        for aux_name in ["approval", "title_generation", "vision"]:
            aux_cfg = self._config.get("auxiliary", {}).get(aux_name, {})
            aux_model = aux_cfg.get("model", "")
            aux_key = aux_cfg.get("api_key", "")
            aux_url = aux_cfg.get("base_url", "")
            if aux_model and aux_key and aux_url and aux_model not in self._providers:
                self._providers[aux_model] = {
                    "model": aux_model,
                    "url": aux_url.rstrip("/") + "/chat/completions",
                    "api_key": aux_key,
                }

    def call_with_model(
        self,
        model: str,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 12000,
        timeout: int = 600,
    ) -> str:
        """V5.3: 指定模型调用（hf_builder 并行模式用）"""
        provider = self._providers.get(model)
        if not provider:
            raise RuntimeError(f"模型 {model} 未注册")

        self._rate_limiter.wait_if_needed()
        if not self._rate_limiter.acquire():
            time.sleep(1)
            if not self._rate_limiter.acquire():
                raise RuntimeError(f"账号限流，无法调用 {model}")

        print(f"  [Provider] 指定模型 {model} (RPM={self._rate_limiter.current_rpm})")
        result = self._call_single(provider, prompt, system_prompt, max_tokens, timeout)
        if result:
            self._last_model_used = model
            return result
        raise RuntimeError(f"模型 {model} 调用失败")

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

        策略：
        1. 主力模型 deepseek-v4-pro 优先
        2. pro 失败（429/超时/错误）才尝试 fallback
        3. 账号级限流 + 429 全局退避
        """
        task_cfg = TASK_MODEL_MAP.get(task, TASK_MODEL_MAP["creative"])
        if max_tokens is None:
            max_tokens = task_cfg["max_tokens"]
        # V5.2 Fix B: 使用task级别timeout（creative=600s）
        if timeout == 300:  # 默认值，尝试从task配置读取
            timeout = task_cfg.get("timeout", timeout)

        primary = task_cfg["primary"]
        fallbacks = task_cfg["fallback"]

        # 尝试顺序：primary → fallback
        ordered_models = [primary] + fallbacks

        print(f"  [Provider] 任务={task}, 主力={primary}, RPM={self._rate_limiter.current_rpm}")

        for model in ordered_models:
            provider = self._providers.get(model)
            if not provider:
                continue

            # V5.2 Fix E: 如果之前有模型收到429（账号级限流），跳过所有fallback
            if self._rate_limiter._global_cooldown_until > time.time():
                if model != primary:
                    print(f"  [Provider] 账号级冷却中，跳过 fallback {model}")
                    continue
                else:
                    # primary也冷却中，等待冷却结束
                    self._rate_limiter.wait_if_needed()

            # 账号级限流
            self._rate_limiter.wait_if_needed()
            if not self._rate_limiter.acquire():
                time.sleep(1)
                if not self._rate_limiter.acquire():
                    print(f"  [Provider] 账号限流，跳过 {model}")
                    continue

            is_primary = (model == primary)
            label = "★主力" if is_primary else "↳fallback"
            print(f"  [Provider] {label} {model}")

            result = self._call_single(provider, prompt, system_prompt, max_tokens, timeout)

            if result:
                self._last_model_used = model  # V5.2 Fix C
                return result

            # V5.2 Fix E: 如果 primary 收到 429，直接停止（账号级限流，fallback 也会 429）
            if model == primary and self._rate_limiter._global_cooldown_until > time.time():
                print(f"  [Provider] primary {model} 触发账号级限流，跳过所有 fallback")
                break

            print(f"  [Provider] {model} 失败，尝试下一个...")

        raise RuntimeError(f"所有模型均调用失败 (task={task})")

    def _call_single(
        self,
        provider: dict,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        timeout: int,
    ) -> Optional[str]:
        """调用单个 provider"""
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

        model = provider["model"]

        for retry in range(3):
            try:
                resp = requests.post(
                    provider["url"],
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )

                if resp.status_code == 429:
                    self._model_429_count[model] = self._model_429_count.get(model, 0) + 1
                    self._rate_limiter.report_429()
                    wait = min((retry + 1) * 8, 30)
                    print(f"  [Provider] {model} 429 (第{self._model_429_count[model]}次), 等待 {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code == 200:
                    data = resp.json()
                    msg = data.get("choices", [{}])[0].get("message", {})
                    content = msg.get("content", "").strip()

                    content = re.sub(r"^.+? response\s*", "", content, flags=re.DOTALL).strip()
                    if content:
                        return content

                    reasoning = msg.get("reasoning_content", "").strip()
                    if reasoning:
                        return reasoning

                    return content

                # 其他错误
                print(f"  [Provider] {model} HTTP {resp.status_code}: {resp.text[:100]}")
                if retry < 2:
                    time.sleep((retry + 1) * 3)

            except requests.Timeout:
                print(f"  [Provider] {model} 超时")
                if retry < 2:
                    time.sleep((retry + 1) * 5)
            except Exception as e:
                print(f"  [Provider] {model} 错误: {e}")
                if retry < 2:
                    time.sleep((retry + 1) * 3)

        return None

    @property
    def available_models(self) -> list[str]:
        return list(self._providers.keys())

    @property
    def last_model_used(self) -> str:
        """V5.2 Fix C: 供 cost_tracker 读取实际使用的模型名"""
        return self._last_model_used

    def support_envelope(self) -> dict:
        return {
            "providers": len(self._providers),
            "models": self.available_models,
            "tasks": list(TASK_MODEL_MAP.keys()),
            "rpm": self._rate_limiter.current_rpm,
        }


# ============================================================
# 便捷函数
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
    return get_registry().call(task, prompt, system_prompt, max_tokens, timeout)
