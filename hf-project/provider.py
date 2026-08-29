#!/usr/bin/env python3
"""
provider.py — LLM Provider 抽象层 v3 (DeepSeek 官方 API)

核心改进：
- 切换至 DeepSeek 官方 API (api.deepseek.com)
- 只用 deepseek-v4-pro + deepseek-v4-flash 两个模型
- 账号级限流 + 429 全局退避
- 按任务智能分配模型（轻→flash，重→pro）

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

# V5.4: 全部切 DeepSeek 官方 API，只有 pro 和 flash 两个模型
# 原则：轻任务用 flash（快+便宜），重任务用 pro（强）
TASK_MODEL_MAP = {
    "research": {
        "description": "信息采集、热点分析",
        "primary": "deepseek-v4-flash",
        "fallback": ["deepseek-v4-pro"],
        "max_tokens": 4000,
    },
    "selection": {
        "description": "选题评估、多维度打分",
        "primary": "deepseek-v4-flash",
        "fallback": ["deepseek-v4-pro"],
        "max_tokens": 4000,
    },
    "creative": {
        "description": "脚本创作、设计系统、分镜（V8: flash主力——v4-pro 推理前奏污染 JSON，flash 更快更稳）",
        "primary": "deepseek-v4-flash",
        "fallback": ["deepseek-v4-pro"],
        "max_tokens": 12000,
        "timeout": 600,
    },
    "creative_light": {
        "description": "歌词、设计系统等轻创意任务（并行时不抢pro）",
        "primary": "deepseek-v4-flash",
        "fallback": ["deepseek-v4-pro"],
        "max_tokens": 8000,
        "timeout": 300,
    },
    "creative_html": {
        "description": "hf_builder 场景 HTML 生成（V7: flash主力，pro兜底——flash更快更稳）",
        "primary": "deepseek-v4-flash",
        "fallback": ["deepseek-v4-pro"],
        "max_tokens": 12000,
        "flash_max_tokens": 12000,
        "timeout": 600,
    },
    "analysis": {
        "description": "质量诊断、内容审核",
        "primary": "deepseek-v4-flash",
        "fallback": ["deepseek-v4-pro"],
        "max_tokens": 4000,
    },
}

# V7: hf_builder 并行模型 — pro-only（flash 有 thinking 污染，禁用）
HF_PARALLEL_MODELS = [
    "deepseek-v4-pro",
    "deepseek-v4-pro",
    "deepseek-v4-pro",
]


# ============================================================
# V55: LLM 统一配置 — 换模型/供应商只改 llm_config.yaml，不改代码
# ============================================================

def _load_llm_config() -> dict:
    """加载统一配置 E:/Hermes-Agent/workspace/xiaoshan/llm_config.yaml。

    找不到文件时返回 {}，完全走下方硬编码默认（向后兼容）。
    """
    config_path = os.environ.get(
        "VF_LLM_CONFIG",
        str(Path(__file__).resolve().parent.parent.parent / "llm_config.yaml"),
    )
    if not Path(config_path).exists():
        return {}
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


_LLM_CONFIG = _load_llm_config()

# model_override：把任务映射里的模型名做替换（换模型改 llm_config.yaml，不改代码）
_OVERRIDE = _LLM_CONFIG.get("model_override", {})


def _apply_override(model: str) -> str:
    return _OVERRIDE.get(model, model)


# 把 TASK_MODEL_MAP 里的 primary/fallback 做 override
for _cfg in TASK_MODEL_MAP.values():
    if "primary" in _cfg:
        _cfg["primary"] = _apply_override(_cfg["primary"])
    if "fallback" in _cfg:
        _cfg["fallback"] = [_apply_override(m) for m in _cfg["fallback"]]

# 并行模型 override
HF_PARALLEL_MODELS = [_apply_override(m) for m in HF_PARALLEL_MODELS]

# 视觉模型（看图任务）
VISION_MODEL = _apply_override(_LLM_CONFIG.get("vision_model", "deepseek-v4-flash-vision-exp"))


# ============================================================
# 账号级限流器
# ============================================================

class AccountRateLimiter:
    """账号级令牌桶 — 所有模型共享配额"""

    def __init__(self, max_rpm: int = 100):
        """
        Args:
            max_rpm: 每分钟最大请求数
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
        # V7: 100 RPM（官方 DeepSeek 并发 500，远未到瓶颈）
        max_rpm = int(os.environ.get("VF_MAX_RPM", "100"))
        self._rate_limiter = AccountRateLimiter(max_rpm=max_rpm)
        self._model_429_count: dict[str, int] = {}  # 每个模型的 429 计数
        self._last_model_used: str = ""
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

        # V5.4: DEEPSEEK_API_KEY only
        self._api_key = (
            os.environ.get("DEEPSEEK_API_KEY")
            or self._config.get("model", {}).get("api_key", "")
        )
        # V5.4: DeepSeek 官方 API endpoint
        self._base_url = (
            os.environ.get("VF_BASE_URL")
            or self._config.get("model", {}).get("base_url", "")
            or "https://api.deepseek.com/v1"
        )

    def _discover(self):
        # V55: 用 llm_config.yaml 的 providers 注册所有模型（支持多供应商）
        providers_cfg = _LLM_CONFIG.get("providers", {})
        if providers_cfg:
            for _name, pcfg in providers_cfg.items():
                env_name = pcfg.get("api_key_env", "")
                # api_key：环境变量优先；仅 deepseek 供应商在环境变量空时 fallback 到 self._api_key（config.yaml 读到的）
                api_key = os.environ.get(env_name, "")
                if not api_key and env_name == "DEEPSEEK_API_KEY":
                    api_key = self._api_key
                base_url = pcfg.get("base_url", self._base_url)
                for model in pcfg.get("models", []):
                    self._providers[model] = {
                        "model": model,
                        "url": base_url.rstrip("/") + "/chat/completions",
                        "api_key": api_key,
                    }
            return

        # 向后兼容：无 llm_config.yaml 时，走原 deepseek 硬注册逻辑
        if not self._api_key:
            return

        # V5.4: 硬注册 pro/flash/vision（确保始终可用，不依赖 config.yaml）
        for model_name in ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp"]:
            if model_name not in self._providers:
                self._providers[model_name] = {
                    "model": model_name,
                    "url": self._base_url.rstrip("/") + "/chat/completions",
                    "api_key": self._api_key,
                }

        # V5.4: 只保留 DeepSeek 模型，过滤掉 config.yaml/环境变量泄漏的其他模型
        self._providers = {
            k: v for k, v in self._providers.items()
            if k in ("deepseek-v4-pro", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp")
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
        1. 主力模型优先
        2. 主力失败才尝试 fallback
        3. 账号级限流 + 429 全局退避
        """
        task_cfg = TASK_MODEL_MAP.get(task, TASK_MODEL_MAP["creative"])
        if max_tokens is None:
            max_tokens = task_cfg["max_tokens"]
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

            # 如果之前有模型收到429（账号级限流），跳过所有fallback
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
                self._last_model_used = model
                return result

            # 如果 primary 收到 429，直接停止（账号级限流，fallback 也会 429）
            if model == primary and self._rate_limiter._global_cooldown_until > time.time():
                print(f"  [Provider] primary {model} 触发账号级限流，跳过所有 fallback")
                break

            print(f"  [Provider] {model} 失败，尝试下一个...")

        raise RuntimeError(f"所有模型均调用失败 (task={task})")

    def call_vision(
        self,
        prompt: str,
        image_path: str = None,
        max_tokens: int = 800,
        timeout: int = 60,
    ) -> Optional[str]:
        """调用 deepseek-v4-flash-vision-exp 视觉模型（支持图片输入）"""
        import base64 as _b64

        # reasoning 模型：reasoning_content 会先占 3000+ tokens，需给足空间让 content 输出
        max_tokens = max(max_tokens, 2000)

        model = VISION_MODEL
        provider = self._providers.get(model)
        if not provider:
            provider = {
                "model": model,
                "url": self._base_url.rstrip("/") + "/chat/completions",
                "api_key": self._api_key,
            }

        # 构建 content（文本 + 图片）
        content = [{"type": "text", "text": prompt}]
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_b64 = _b64.b64encode(f.read()).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
            })

        messages = [{"role": "user", "content": content}]
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": provider["model"],
            "messages": messages,
            "max_tokens": max_tokens,
        }

        try:
            resp = requests.post(provider["url"], headers=headers, json=payload, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("choices", [{}])[0].get("message", {})
                content_text = msg.get("content", "").strip()
                if content_text:
                    return content_text
                # content 为空说明被截断（reasoning 占了全部 token），不返回 reasoning（那是思考过程不是答案）
                return None
            print(f"  [Provider] vision {model} HTTP {resp.status_code}: {resp.text[:150]}")
        except Exception as e:
            print(f"  [Provider] vision {model} 错误: {e}")
        return None

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
        model = provider["model"]
        # V39: reasoning 模型（flash/pro）reasoning_content 会随机暴走占大量 tokens，
        # 强制给 content 留足空间（否则 content 被挤空，JSON 解析失败）
        if any(k in model for k in ("flash", "reasoner", "pro")):
            max_tokens = max(max_tokens, 16000)
        payload = {
            "model": model,
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

                    # 清洗 reasoning 前缀（某些模型会输出）
                    content = re.sub(r"^.+? response\s*", "", content, flags=re.DOTALL).strip()
                    if content:
                        return content

                    # V39: reasoning_content 是思考过程不是答案，绝不 fallback（否则 JSON 解析必失败）
                    # content 为空说明 max_tokens 被 reasoning 吃光，应返回 None 让上层重试/加大 max_tokens
                    return None

                # 402 Insufficient Balance 等致命错误不重试
                if resp.status_code == 402:
                    print(f"  [Provider] {model} 402 余额不足，不重试")
                    return None

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
        """供 cost_tracker 读取实际使用的模型名"""
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
