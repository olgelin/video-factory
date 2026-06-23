"""
core/checkpoint.py — 断点续传
保存/加载pipeline执行状态
"""

import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class CheckpointManager:
    """断点续传管理"""
    
    def __init__(self, output_dir: str):
        self.dir = Path(output_dir) / "checkpoints"
        self.dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, step: int, context: dict, skill_name: str = ""):
        """保存checkpoint"""
        data = {
            "step": step,
            "skill_name": skill_name,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }
        
        filepath = self.dir / f"step{step:02d}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Checkpoint saved: step {step} ({skill_name})")
        return filepath
    
    def load(self, step: int) -> dict:
        """加载checkpoint"""
        filepath = self.dir / f"step{step:02d}.json"
        if not filepath.exists():
            return None
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"Checkpoint loaded: step {step}")
        return data
    
    def get_latest(self) -> int:
        """获取最新checkpoint步骤号"""
        checkpoints = sorted(self.dir.glob("step*.json"))
        if not checkpoints:
            return 0
        
        # 从文件名提取步骤号
        latest = checkpoints[-1]
        step = int(latest.stem.replace("step", ""))
        return step
    
    def list_checkpoints(self) -> list:
        """列出所有checkpoint"""
        checkpoints = []
        for f in sorted(self.dir.glob("step*.json")):
            step = int(f.stem.replace("step", ""))
            data = self.load(step)
            if data:
                checkpoints.append({
                    "step": step,
                    "skill_name": data.get("skill_name", ""),
                    "timestamp": data.get("timestamp", ""),
                })
        return checkpoints
    
    def clear(self):
        """清除所有checkpoint"""
        for f in self.dir.glob("step*.json"):
            f.unlink()
        logger.info("All checkpoints cleared")
