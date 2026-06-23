#!/usr/bin/env python3
"""
video_upscaler/skill.py — Video2X高清修复
功能：用Video2X将视频从720p/1080p upscale到2K/4K
输出：upscaled视频文件

Video2X是独立exe，不走Python venv，直接subprocess调用
"""

import os
import subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
TOOLS_DIR = Path(__file__).parent.parent.parent / "tools"


def _find_video2x() -> str:
    """查找video2x可执行文件"""
    # 优先本地tools/video2x/
    local = TOOLS_DIR / "video2x" / "video2x.exe"
    if local.exists():
        return str(local)
    # 回退PATH
    return "video2x"


def run(context: dict) -> dict:
    """主入口：Video2X高清修复"""

    # 输入视频
    video_path = context.get("video_path") or str(OUTPUT_DIR / "step10_video.mp4")
    if not os.path.exists(video_path):
        print(f"  ❌ [upscaler] 找不到视频: {video_path}")
        return context

    # 参数
    scale = context.get("upscale_factor", 2)  # 默认2x
    denoise = context.get("upscale_denoise", 0)  # 降噪强度 0-10
    model = context.get("upscale_model", "realesrgan-x2plus")

    # 输出路径
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "step10_upscaled.mp4"

    v2x = _find_video2x()

    print(f"  [upscaler] 输入: {video_path}")
    print(f"  [upscaler] 参数: scale={scale}x, denoise={denoise}, model={model}")
    print(f"  [upscaler] 工具: {v2x}")

    # Video2X CLI调用
    cmd = [
        v2x,
        "-i", video_path,
        "-o", str(output_path),
        "-s", str(scale),
        "-n", str(denoise),
        "-p", model,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30分钟
        )

        if result.returncode == 0 and output_path.exists():
            # 获取输出文件大小
            size_mb = output_path.stat().st_size / 1024 / 1024
            print(f"  [upscaler] ✅ 高清修复完成: {output_path} ({size_mb:.1f}MB)")
            context["video_path"] = str(output_path)
            context["upscaled"] = True
        else:
            print(f"  ❌ [upscaler] 渲染失败 (exit={result.returncode})")
            if result.stderr:
                print(f"     stderr: {result.stderr[-300:]}")
            print(f"  [upscaler] 跳过高清修复，使用原始视频")

    except subprocess.TimeoutExpired:
        print(f"  ❌ [upscaler] 超时（1800s），跳过高清修复")
    except FileNotFoundError:
        print(f"  ❌ [upscaler] Video2X未安装，跳过高清修复")
    except Exception as e:
        print(f"  ❌ [upscaler] 异常: {e}")

    return context


if __name__ == "__main__":
    test_context = {
        "video_path": str(OUTPUT_DIR / "step10_video.mp4"),
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  视频路径: {result.get('video_path')}")
    print(f"  已高清: {result.get('upscaled', False)}")
