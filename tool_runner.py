#!/usr/bin/env python3
"""
工具调用器 - 统一的subprocess接口
所有ML工具通过此模块调用，与pipeline主环境完全隔离
"""

import subprocess
import json
import os
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent.parent / "tools"


def call_tool(tool_name: str, cli_args: list, timeout: int = 600) -> dict:
    """
    调用工具的CLI接口

    Args:
        tool_name: 工具名 (voxcpm, acestep, transcriber)
        cli_args: CLI参数列表
        timeout: 超时秒数

    Returns:
        dict: 工具输出的JSON元数据
    """
    tool_dir = TOOLS_DIR / tool_name
    venv_python = tool_dir / ".venv" / "Scripts" / "python.exe"
    cli_script = tool_dir / "cli.py"

    if not venv_python.exists():
        raise FileNotFoundError(f"工具venv不存在: {venv_python}")
    if not cli_script.exists():
        raise FileNotFoundError(f"工具CLI不存在: {cli_script}")

    cmd = [str(venv_python), str(cli_script)] + cli_args

    print(f"  [tool-runner] 调用 {tool_name}: {' '.join(cli_args[:6])}...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(TOOLS_DIR.parent),  # video-factory根目录
        )

        if result.returncode != 0:
            print(f"  ❌ [tool-runner] {tool_name} 失败 (exit={result.returncode})")
            if result.stderr:
                print(f"     stderr: {result.stderr[-300:]}")
            return {"error": f"{tool_name} failed", "stderr": result.stderr[-500:]}

        # 解析stdout中的JSON
        stdout = result.stdout.strip()
        if stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                # stdout可能包含非JSON内容（如print语句），尝试找最后一行JSON
                for line in reversed(stdout.split('\n')):
                    line = line.strip()
                    if line.startswith('{'):
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            continue
                return {"error": f"{tool_name} 输出非JSON", "stdout": stdout[-500:]}
        else:
            return {"error": f"{tool_name} 无输出"}

    except subprocess.TimeoutExpired:
        print(f"  ❌ [tool-runner] {tool_name} 超时 ({timeout}s)")
        return {"error": f"{tool_name} timeout"}
    except Exception as e:
        print(f"  ❌ [tool-runner] {tool_name} 异常: {e}")
        return {"error": str(e)}


def call_voxcpm(input_path: str, output_path: str, speed: float = 1.0,
                ref_audio: str = None, cfg: float = 2.0, steps: int = 10) -> dict:
    """调用VoxCPM2 TTS"""
    args = ["--input", input_path, "--output", output_path, "--speed", str(speed),
            "--cfg", str(cfg), "--steps", str(steps)]
    if ref_audio:
        args += ["--ref-audio", ref_audio]
    return call_tool("voxcpm", args, timeout=600)


def call_acestep(lyrics_path: str, output_path: str, duration: float = 120,
                 captions: str = "electronic, tech, cinematic, 100 BPM") -> dict:
    """调用ACE-Step BGM"""
    args = ["--lyrics", lyrics_path, "--output", output_path,
            "--duration", str(duration), "--captions", captions]
    return call_tool("acestep", args, timeout=600)


def call_transcriber(input_path: str, output_path: str, srt_path: str = None) -> dict:
    """调用Transcriber"""
    args = ["--input", input_path, "--output", output_path]
    if srt_path:
        args += ["--srt-output", srt_path]
    return call_tool("transcriber", args, timeout=300)
