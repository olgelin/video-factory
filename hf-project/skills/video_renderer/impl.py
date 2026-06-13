"""
video_renderer/skill.py — HyperFrames渲染
功能：用HyperFrames CLI渲染HTML为MP4
输出：video.mp4

简化版：只调用CLI，不做任何HTML生成。
"""

import os
import subprocess
from pathlib import Path

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
VIDEO_PATH = OUTPUT_DIR / "step10_video.mp4"
HF_PROJECT_DIR = Path(__file__).parent.parent.parent / "hf_render_project"


def _fix_duplicate_styles(project_dir: str):
    """预检：修复HTML中的重复style属性（防止渲染空白帧）"""
    import re
    comp_dir = Path(project_dir) / "compositions"
    if not comp_dir.exists():
        return
    
    fixed = 0
    for html_file in comp_dir.glob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        original = content
        
        # 修复同一元素上的重复 style="..." style="..."
        # Pattern: style="A" style="B" → style="A; B"
        content = re.sub(
            r'(style="[^"]*")\s+(style="[^"]*")',
            lambda m: m.group(1).rstrip('"') + '; ' + m.group(2).lstrip('style="'),
            content
        )
        
        if content != original:
            html_file.write_text(content, encoding="utf-8")
            fixed += 1
    
    if fixed > 0:
        print(f"  [video-renderer] 预检修复: {fixed} 个HTML文件的重复style属性")


def run_hyperframes_render(project_dir: str, output_path: str) -> bool:
    """运行HyperFrames渲染"""
    print(f"  [video-renderer] 渲染: {project_dir}")

    # 运行hyperframes render
    cmd = f"npx hyperframes render . --output {output_path}"

    try:
        result = subprocess.run(
            cmd, shell=True, cwd=project_dir, capture_output=True, text=True, timeout=600
        )

        if result.returncode == 0:
            print(f"  [video-renderer] ✅ 渲染完成: {output_path}")
            return True
        else:
            print(f"  ❌ [video-renderer] 渲染失败")
            if result.stdout:
                print(f"    stdout: {result.stdout[:200]}")
            if result.stderr:
                print(f"    stderr: {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ❌ [video-renderer] 渲染超时（600s）")
        return False
    except Exception as e:
        print(f"  ❌ [video-renderer] 渲染错误: {e}")
        return False


def run(context: dict) -> dict:
    """主入口：渲染视频"""

    topic = context.get("topic", "未知话题")
    print(f"  [video-renderer] 渲染 '{topic}' 的视频...")

    # 获取项目目录
    project_dir = context.get("hf_project_dir") or str(HF_PROJECT_DIR)
    if not os.path.exists(project_dir):
        print(f"  ❌ [video-renderer] 项目目录不存在: {project_dir}")
        return context

    # 检查index.html
    index_path = Path(project_dir) / "index.html"
    if not index_path.exists():
        print(f"  ❌ [video-renderer] index.html不存在: {index_path}")
        return context

    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 预检：修复HTML中的重复style属性
    _fix_duplicate_styles(project_dir)

    # 渲染
    success = run_hyperframes_render(project_dir, str(VIDEO_PATH))

    if success:
        # 获取视频信息
        import subprocess
        result = subprocess.run(
            f"ffprobe -v quiet -print_format json -show_format {VIDEO_PATH}",
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            duration = float(info.get("format", {}).get("duration", 0))
            size = int(info.get("format", {}).get("size", 0))

            print(f"  [video-renderer] 时长: {duration:.1f}s, 大小: {size/1024:.0f}KB")

            context["video_path"] = str(VIDEO_PATH)
            context["video_duration"] = duration
            context["video_size"] = size
    else:
        print(f"  ❌ [video-renderer] 渲染失败")

    return context


if __name__ == "__main__":
    # 测试
    test_context = {
        "topic": "2026高考第一批显眼包出现了",
        "hf_project_dir": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/hf_render_project",
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  视频路径: {result.get('video_path')}")
    print(f"  时长: {result.get('video_duration')}")
