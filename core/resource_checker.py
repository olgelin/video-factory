"""
core/resource_checker.py — 资源预检
在pipeline开始前检查GPU/CPU/内存/磁盘
"""

import os
import shutil
import logging

logger = logging.getLogger(__name__)


class ResourceChecker:
    """资源预检"""
    
    @staticmethod
    def check_gpu(min_memory_gb: float = 6.0) -> dict:
        """检查GPU内存"""
        try:
            import torch
            if not torch.cuda.is_available():
                return {"passed": False, "message": "CUDA not available", "available": 0}
            free_memory = torch.cuda.mem_get_info()[0] / (1024**3)
            return {
                "passed": free_memory >= min_memory_gb,
                "message": f"GPU memory: {free_memory:.1f}GB / {min_memory_gb}GB required",
                "available": free_memory
            }
        except ImportError:
            return {"passed": False, "message": "torch not installed", "available": 0}
    
    @staticmethod
    def check_disk(min_space_gb: float = 10.0, path: str = "/") -> dict:
        """检查磁盘空间"""
        try:
            free_space = shutil.disk_usage(path).free / (1024**3)
            return {
                "passed": free_space >= min_space_gb,
                "message": f"Disk space: {free_space:.1f}GB / {min_space_gb}GB required",
                "available": free_space
            }
        except Exception as e:
            return {"passed": False, "message": f"Disk check failed: {e}", "available": 0}
    
    @staticmethod
    def check_ram(min_gb: float = 8.0) -> dict:
        """检查内存"""
        try:
            import psutil
            available = psutil.virtual_memory().available / (1024**3)
            return {
                "passed": available >= min_gb,
                "message": f"RAM: {available:.1f}GB / {min_gb}GB required",
                "available": available
            }
        except ImportError:
            # psutil不可用时跳过检查
            return {"passed": True, "message": "psutil not installed, skipped", "available": 0}
    
    @classmethod
    def preflight(cls, gpu_gb: float = 6.0, disk_gb: float = 10.0, ram_gb: float = 8.0) -> dict:
        """执行所有预检"""
        checks = {
            "gpu": cls.check_gpu(gpu_gb),
            "disk": cls.check_disk(disk_gb),
            "ram": cls.check_ram(ram_gb),
        }
        
        passed = all(c["passed"] for c in checks.values())
        
        if not passed:
            failed = [k for k, v in checks.items() if not v["passed"]]
            logger.warning(f"Preflight checks failed: {failed}")
        
        return {
            "passed": passed,
            "checks": checks,
        }
