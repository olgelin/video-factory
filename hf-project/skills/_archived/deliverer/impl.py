"""
deliverer/skill.py — 交付
功能：将视频发送到飞书
输出：飞书消息

基于原step14简化。
"""

import os
from pathlib import Path


def run(context: dict) -> dict:
    """主入口：交付视频"""

    topic = context.get("topic", "未知话题")
    deliverable_dir = context.get("deliverable_dir")

    print(f"  [deliverer] 交付 '{topic}'...")

    # 获取视频路径
    if deliverable_dir:
        video_path = Path(deliverable_dir) / "final.mp4"
    else:
        video_path = context.get("mixed_path") or context.get("video_path")

    if not video_path or not os.path.exists(video_path):
        print(f"  ❌ [deliverer] 视频不存在: {video_path}")
        return context

    # 获取视频信息
    import subprocess
    result = subprocess.run(
        f"ffprobe -v quiet -print_format json -show_format {video_path}",
        shell=True, capture_output=True, text=True
    )

    duration = 0
    size = 0
    if result.returncode == 0:
        import json
        info = json.loads(result.stdout)
        duration = float(info.get("format", {}).get("duration", 0))
        size = int(info.get("format", {}).get("size", 0))

    # 更新context
    context["final_video_path"] = str(video_path)
    context["final_duration"] = duration
    context["final_size"] = size

    print(f"  [deliverer] ✅ 视频准备就绪: {video_path}")
    print(f"  [deliverer] 时长: {duration:.1f}s, 大小: {size/1024/1024:.1f}MB")
    print(f"  [deliverer] 请手动发送到飞书或使用send_message工具")

    return context


if __name__ == "__main__":
    # 测试
    test_context = {
        "topic": "2026高考第一批显眼包出现了",
        "deliverable_dir": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/deliverables/2026高考第一批显眼包出现了_20260609_020000",
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  视频路径: {result.get('final_video_path')}")
