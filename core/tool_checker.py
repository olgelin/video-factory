#!/usr/bin/env python3
"""
工具环境预检 — 确保所有外部工具版本正确、环境就绪
每次pipeline运行前调用，版本不匹配时报错并给出修复命令
"""

import subprocess
import sys
import json
from pathlib import Path

# 版本锁定 — 升级时只改这里
REQUIRED = {
    "hyperframes": "0.7.3",
    "video2x": "6.4.0",
}


def check_hyperframes():
    """检查HyperFrames CLI版本"""
    # 直接用全局cmd路径，避免npx超时
    hf_cmd = "E:/AI-openclaw/env/nodejs/node_global/hyperframes.cmd"
    try:
        r = subprocess.run([hf_cmd, "--version"],
                           capture_output=True, text=True, timeout=15)
        version = r.stdout.strip()
        if version == REQUIRED["hyperframes"]:
            return True, version
        else:
            return False, f"需要{REQUIRED['hyperframes']}，当前{version}，运行: npm install -g hyperframes@{REQUIRED['hyperframes']}"
    except Exception as e:
        return False, f"未安装，运行: npm install -g hyperframes@{REQUIRED['hyperframes']}"


def check_video2x():
    """检查Video2X"""
    v2x = Path(__file__).parent.parent / "tools" / "video2x" / "video2x.exe"
    if v2x.exists():
        return True, str(v2x)
    # 也检查PATH
    try:
        r = subprocess.run(["video2x", "--version"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return True, "PATH"
    except FileNotFoundError:
        pass
    return False, f"未安装，下载 https://github.com/k4yt3x/video2x/releases/tag/{REQUIRED['video2x']} 放到 tools/video2x/"


def check_tool_venvs():
    """检查3个ML工具独立venv"""
    base = Path(__file__).parent.parent / "tools"
    results = {}
    for tool in ["voxcpm", "acestep", "transcriber"]:
        venv = base / tool / ".venv" / "Scripts" / "python.exe"
        cli = base / tool / "cli.py"
        if venv.exists() and cli.exists():
            results[tool] = "OK"
        else:
            results[tool] = f"MISSING (venv={venv.exists()}, cli={cli.exists()})"
    return results


def run_all():
    """运行全部检查"""
    print("=" * 60)
    print("🔧 工具环境预检")
    print("=" * 60)

    all_ok = True

    # HyperFrames
    ok, msg = check_hyperframes()
    status = "✅" if ok else "❌"
    print(f"  {status} HyperFrames: {msg}")
    if not ok:
        all_ok = False

    # Video2X
    ok, msg = check_video2x()
    status = "✅" if ok else "⚠️"
    print(f"  {status} Video2X: {msg}")
    # Video2X是可选的，不影响pipeline

    # ML工具venvs
    venvs = check_tool_venvs()
    for tool, status in venvs.items():
        icon = "✅" if status == "OK" else "❌"
        print(f"  {icon} {tool}: {status}")
        if status != "OK":
            all_ok = False

    print("=" * 60)
    if all_ok:
        print("  ✅ 所有工具环境就绪")
    else:
        print("  ❌ 部分工具缺失，请按提示修复")
    print("=" * 60)

    return all_ok


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
