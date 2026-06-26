#!/usr/bin/env python3
"""
cost_tracker.py — API 费用追踪器

从 OpenMontage 借鉴，适配 video-factory：
- 每次 LLM 调用前 estimate → 完成后 reconcile
- 支持 budget warn/cap 模式
- 输出 cost_log.json 到 output 目录

费用估算（火山引擎 Ark 价格，RMB/1M tokens）：
- deepseek-v4-pro:   输入 ¥2, 输出 ¥8
- deepseek-v4-flash: 输入 ¥0.5, 输出 ¥2
- glm-5.2:           输入 ¥5, 输出 ¥20
- minimax-m3:        输入 ¥1, 输出 ¥4
- kimi-k2.7-code:    输入 ¥2, 输出 ¥8
"""

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# 模型价格表（RMB / 1M tokens）
MODEL_PRICES = {
    "deepseek-v4-pro":    {"input": 2.0,  "output": 8.0},
    "deepseek-v4-flash":  {"input": 0.5,  "output": 2.0},
    "glm-5.2":            {"input": 5.0,  "output": 20.0},
    "minimax-m3":         {"input": 1.0,  "output": 4.0},
    "kimi-k2.7-code":     {"input": 2.0,  "output": 8.0},
    # 默认
    "default":            {"input": 2.0,  "output": 8.0},
}

# RMB → USD 汇率（近似）
RMB_TO_USD = 0.14


class CostTracker:
    """API 费用追踪器"""

    def __init__(
        self,
        output_dir: str = None,
        budget_total_usd: float = 2.0,
        reserve_pct: float = 0.10,
        mode: str = "warn",  # observe | warn | cap
    ):
        self.output_dir = Path(output_dir) if output_dir else Path("output")
        self.budget_total_usd = budget_total_usd
        self.reserve_pct = reserve_pct
        self.mode = mode
        self.entries: list[dict] = []
        self._active_estimates: dict[str, dict] = {}

        # 加载历史
        self._log_path = self.output_dir / "cost_log.json"
        if self._log_path.exists():
            try:
                with open(self._log_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.entries = data.get("entries", [])
            except Exception:
                pass

    def estimate(
        self,
        stage_name: str,
        provider: str = "unknown",
        model: str = "",
        prompt_chars: int = 0,
        expected_output_chars: int = 0,
    ) -> str:
        """
        预估费用并预留预算

        Returns:
            estimate_id (用于后续 reconcile)
        """
        # 估算 token 数（中文约 1 char ≈ 0.5 token）
        input_tokens = prompt_chars * 0.5
        output_tokens = expected_output_chars * 0.5

        # 查价格
        prices = MODEL_PRICES.get(model, MODEL_PRICES["default"])
        cost_rmb = (input_tokens / 1_000_000) * prices["input"] + \
                   (output_tokens / 1_000_000) * prices["output"]
        cost_usd = cost_rmb * RMB_TO_USD

        estimate_id = str(uuid.uuid4())[:8]
        entry = {
            "id": estimate_id,
            "stage": stage_name,
            "provider": provider,
            "model": model,
            "status": "estimated",
            "estimated_usd": round(cost_usd, 6),
            "actual_usd": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._active_estimates[estimate_id] = entry

        # Budget check
        if self.mode == "cap" and self.budget_remaining_usd < cost_usd:
            raise BudgetExceededError(
                f"预算不足: 需要 ${cost_usd:.4f}, 剩余 ${self.budget_remaining_usd:.4f}"
            )

        if self.mode == "warn" and self.budget_remaining_usd < cost_usd:
            print(f"  ⚠️ [Cost] 预算预警: 剩余 ${self.budget_remaining_usd:.4f}, "
                  f"本次预估 ${cost_usd:.4f}")

        return estimate_id

    def reconcile(self, stage_name: str, success: bool = True, actual_chars: int = 0):
        """
        结算费用（根据 stage_name 匹配最近的 estimate）
        """
        # 找到匹配的 estimate
        for eid, entry in list(self._active_estimates.items()):
            if entry["stage"] == stage_name:
                if success:
                    # 粗略估算实际费用
                    prices = MODEL_PRICES.get(entry["model"], MODEL_PRICES["default"])
                    output_tokens = actual_chars * 0.5
                    cost_rmb = (output_tokens / 1_000_000) * prices["output"]
                    entry["actual_usd"] = round(cost_rmb * RMB_TO_USD, 6)
                    entry["status"] = "completed"
                else:
                    entry["status"] = "failed"

                self.entries.append(entry)
                del self._active_estimates[eid]
                self._save()
                return

    def _save(self):
        """持久化到 cost_log.json"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self._log_path, "w", encoding="utf-8") as f:
            json.dump({
                "updated": datetime.now(timezone.utc).isoformat(),
                "entries": self.entries[-50:],  # 只保留最近 50 条
                "summary": self.snapshot(),
            }, f, ensure_ascii=False, indent=2)

    @property
    def budget_spent_usd(self) -> float:
        return sum(
            e.get("actual_usd", 0)
            for e in self.entries
            if e.get("status") in ("completed", "failed")
        )

    @property
    def budget_remaining_usd(self) -> float:
        return self.budget_total_usd - self.budget_spent_usd

    def snapshot(self) -> dict:
        return {
            "total_spent_usd": round(self.budget_spent_usd, 4),
            "budget_total_usd": self.budget_total_usd,
            "budget_remaining_usd": round(self.budget_remaining_usd, 4),
            "total_calls": len(self.entries),
            "successful_calls": sum(
                1 for e in self.entries if e.get("status") == "completed"
            ),
        }

    def print_summary(self):
        """打印费用摘要"""
        s = self.snapshot()
        print(f"\n{'='*40}")
        print(f"💰 费用摘要")
        print(f"{'='*40}")
        print(f"  总花费:     ${s['total_spent_usd']:.4f}")
        print(f"  预算剩余:   ${s['budget_remaining_usd']:.4f}")
        print(f"  总调用:     {s['total_calls']} 次")
        print(f"  成功:       {s['successful_calls']} 次")
        print(f"  日志:       {self._log_path}")


class BudgetExceededError(Exception):
    """预算超支"""
    pass
