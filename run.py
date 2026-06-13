#!/usr/bin/env python3
"""Video Factory 运行脚本 - 自动加载.env并执行pipeline"""
import os
import sys
import subprocess
from pathlib import Path

# 加载.env
env_file = Path(__file__).parent / "video-factory-clawhub" / ".env"
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())
    print(f"✅ 已加载: {env_file}")
else:
    print(f"⚠️ 未找到: {env_file}")

# 检查Python路径
python = sys.executable
print(f"Python: {python}")

# 检查CUDA
try:
    import torch
    print(f"PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}")
except:
    print("⚠️ PyTorch未安装或无法导入")

# 运行pipeline
main_py = Path(__file__).parent / "main_full.py"
if not main_py.exists():
    print(f"❌ 找不到: {main_py}")
    sys.exit(1)

print(f"\n运行: {main_py}")
print(f"参数: {' '.join(sys.argv[1:])}")
print("=" * 60)

# 传递所有命令行参数
cmd = [python, str(main_py)] + sys.argv[1:]
sys.exit(subprocess.call(cmd))
