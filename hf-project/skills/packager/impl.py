"""
packager/skill.py — 封装导出
功能：将视频和所有素材打包到deliverables目录
输出：deliverables/<topic>_<timestamp>/

基于原step12简化。
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

# 输出路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DELIVERABLES_DIR = PROJECT_ROOT / "deliverables"


def run(context: dict) -> dict:
    """主入口：封装导出"""

    topic = context.get("topic", "未知话题")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"  [packager] 封装 '{topic}'...")

    # 创建输出目录
    output_name = f"{topic}_{timestamp}"
    output_dir = DELIVERABLES_DIR / output_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # 复制视频
    video_path = context.get("mixed_path") or context.get("video_path")
    if video_path and os.path.exists(video_path):
        dest_video = output_dir / "final.mp4"
        shutil.copy2(video_path, dest_video)
        print(f"  [packager] 视频: {dest_video}")
    else:
        print(f"  ⚠️ [packager] 没有视频文件")

    # 复制配音
    voice_path = context.get("voice_path")
    if voice_path and os.path.exists(voice_path):
        dest_voice = output_dir / "voice.wav"
        shutil.copy2(voice_path, dest_voice)

    # 复制脚本
    script_path = context.get("script_path")
    if script_path and os.path.exists(script_path):
        dest_script = output_dir / "script.json"
        shutil.copy2(script_path, dest_script)

    # 复制storyboard
    storyboard_path = context.get("storyboard_path")
    if storyboard_path and os.path.exists(storyboard_path):
        dest_sb = output_dir / "storyboard.json"
        shutil.copy2(storyboard_path, dest_sb)

    # 复制design.md
    design_path = context.get("design_md_path")
    if design_path and os.path.exists(design_path):
        dest_design = output_dir / "design.md"
        shutil.copy2(design_path, dest_design)

    # 复制QA报告
    qa_path = context.get("qa_report_path")
    if qa_path and os.path.exists(qa_path):
        dest_qa = output_dir / "qa_report.json"
        shutil.copy2(qa_path, dest_qa)

    # 保存context
    context_path = output_dir / "context.json"
    with open(context_path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2, default=str)

    print(f"  [packager] ✅ 封装完成: {output_dir}")

    # 更新context
    context["deliverable_dir"] = str(output_dir)

    return context


if __name__ == "__main__":
    # 测试
    test_context = {
        "topic": "2026高考第一批显眼包出现了",
        "mixed_path": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/output/step11_final.mp4",
        "voice_path": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/output/step05_voice.wav",
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  输出目录: {result.get('deliverable_dir')}")
