"""
core/metrics.py — 性能监控
记录每步耗时、token消耗、文件大小
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsCollector:
    """性能指标收集器"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.metrics_file = self.output_dir / "metrics.json"
        self.metrics = []
        self._start_time = None
        self._current_skill = None
    
    def start(self, skill_name: str):
        """开始计时"""
        self._start_time = time.time()
        self._current_skill = skill_name
    
    def stop(self, extra: dict = None):
        """停止计时并记录"""
        if self._start_time is None:
            return
        
        elapsed = time.time() - self._start_time
        
        metric = {
            "skill": self._current_skill,
            "duration": round(elapsed, 2),
            "timestamp": datetime.now().isoformat(),
        }
        
        if extra:
            metric.update(extra)
        
        self.metrics.append(metric)
        logger.info(f"{self._current_skill}: {elapsed:.1f}s")
        
        self._start_time = None
        self._current_skill = None
    
    def save(self):
        """保存指标到文件"""
        with open(self.metrics_file, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Metrics saved: {len(self.metrics)} entries")
    
    def get_summary(self) -> dict:
        """获取汇总"""
        if not self.metrics:
            return {}
        
        total_duration = sum(m["duration"] for m in self.metrics)
        slowest = max(self.metrics, key=lambda m: m["duration"])
        
        return {
            "total_duration": round(total_duration, 2),
            "step_count": len(self.metrics),
            "slowest_skill": slowest["skill"],
            "slowest_duration": slowest["duration"],
            "steps": self.metrics,
        }
