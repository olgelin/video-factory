#!/usr/bin/env python3
"""voice_gen subprocess wrapper — 在干净环境中运行voice_gen，避免numpy冲突"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    # 设置干净环境
    env = os.environ.copy()
    
    # 删除PYTHONPATH防止hermes-agent污染
    env.pop('PYTHONPATH', None)
    
    # 设置PATH确保core/venv优先
    core_venv = Path(r'E:\Hermes-Agent\core\venv')
    core_scripts = str(core_venv / 'Scripts')
    core_site = str(core_venv / 'Lib' / 'site-packages')
    
    # PATH: core/venv/Scripts 优先
    path_parts = env.get('PATH', '').split(';')
    path_parts = [p for p in path_parts if 'hermes-agent' not in p.lower()]
    path_parts.insert(0, core_scripts)
    env['PATH'] = ';'.join(path_parts)
    
    # PYTHONPATH: 只有core/venv
    env['PYTHONPATH'] = core_site
    
    # 传递必要环境变量
    env['PYTHONIOENCODING'] = 'utf-8'
    
    # 调用voice_gen
    script = Path(__file__).parent.parent / 'hf-project' / 'skills' / 'voice_gen' / 'impl.py'
    
    # 传递参数
    args = sys.argv[1:]
    
    cmd = [sys.executable, str(script)] + args
    
    print(f"[voice-wrapper] 启动voice_gen: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=False)
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()
