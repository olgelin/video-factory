"""
core/timeout_guard.py — 超时控制
为每个skill执行提供超时保护
"""

import signal
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """超时错误"""
    pass


@contextmanager
def timeout_guard(seconds: int, skill_name: str = "unknown"):
    """超时守卫上下文管理器
    
    用法:
        with timeout_guard(300, "voice_gen"):
            result = run(context)
    """
    def handler(signum, frame):
        raise TimeoutError(f"{skill_name} timed out after {seconds}s")
    
    # 设置信号处理器
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # 恢复原信号处理器
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def run_with_timeout(func, timeout: int = 300, skill_name: str = "unknown"):
    """带超时的函数执行
    
    用法:
        result = run_with_timeout(run, 300, "voice_gen")
    """
    with timeout_guard(timeout, skill_name):
        return func()
