"""
skills/base.py — Skill基类
统一错误处理、输入验证、输出验证、超时控制
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SkillError(Exception):
    """Skill执行错误基类"""
    pass


class InputValidationError(SkillError):
    """输入验证失败"""
    pass


class OutputValidationError(SkillError):
    """输出验证失败"""
    pass


class SkillTimeoutError(SkillError):
    """Skill超时"""
    pass


class SkillBase(ABC):
    """所有skill的基类"""
    
    name: str = "unnamed"
    timeout: int = 300  # 默认超时300秒
    
    def run(self, context: dict) -> dict:
        """统一入口：验证 → 执行 → 验证输出"""
        start_time = time.time()
        
        try:
            # 1. 输入验证
            self.validate_input(context)
            
            # 2. 执行
            result = self.execute(context)
            
            # 3. 输出验证
            self.validate_output(result)
            
            # 4. 记录耗时
            elapsed = time.time() - start_time
            logger.info(f"{self.name} completed in {elapsed:.1f}s")
            
            return result
            
        except InputValidationError as e:
            logger.error(f"{self.name} input validation failed: {e}")
            raise
        except OutputValidationError as e:
            logger.error(f"{self.name} output validation failed: {e}")
            raise
        except SkillTimeoutError as e:
            logger.error(f"{self.name} timed out: {e}")
            return self.handle_timeout(context)
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return self.handle_error(context, e)
    
    @abstractmethod
    def execute(self, context: dict) -> dict:
        """子类实现：核心逻辑"""
        pass
    
    def validate_input(self, context: dict):
        """输入验证（可选覆盖）"""
        pass
    
    def validate_output(self, result: dict):
        """输出验证（可选覆盖）"""
        pass
    
    def handle_timeout(self, context: dict) -> dict:
        """超时处理（可选覆盖）"""
        raise SkillTimeoutError(f"{self.name} timed out after {self.timeout}s")
    
    def handle_error(self, context: dict, error: Exception) -> dict:
        """错误处理（可选覆盖）"""
        raise error
    
    def require_keys(self, context: dict, keys: list):
        """验证context中必须存在的key"""
        missing = [k for k in keys if k not in context or context[k] is None]
        if missing:
            raise InputValidationError(f"{self.name} requires keys: {missing}")
    
    def require_file(self, path: str, name: str = ""):
        """验证文件必须存在"""
        import os
        if not os.path.exists(path):
            raise InputValidationError(f"{self.name} requires file: {path} ({name})")
