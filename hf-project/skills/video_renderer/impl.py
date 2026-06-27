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


def _simplify_composition_gsap(project_dir: str, clip_src: str) -> bool:
    """简化composition中的GSAP动画（渲染失败时的重试策略）"""
    import re
    from pathlib import Path
    
    comp_path = Path(project_dir) / clip_src
    if not comp_path.exists():
        return False
    
    html = comp_path.read_text(encoding="utf-8")
    original = html
    
    # 1. 限制 repeat:-1 最多2个
    repeat_count = len(re.findall(r'repeat:\s*-1', html))
    if repeat_count > 2:
        count = 0
        def _limit(m):
            nonlocal count
            count += 1
            return m.group(0) if count <= 2 else 'repeat: 0'
        html = re.sub(r'repeat:\s*-1', _limit, html)
    
    # 2. 移除多余的 gsap.to（保留前5个）
    to_count = 0
    def _limit_to(m):
        nonlocal to_count
        to_count += 1
        if to_count <= 5:
            return m.group(0)
        return '// ' + m.group(0) + ' // disabled for render'
    html = re.sub(r'(tl|gsap)\.to\(', _limit_to, html)
    
    if html != original:
        comp_path.write_text(html, encoding="utf-8")
        print(f"    [video-renderer] 已简化 {clip_src}: repeat:-1 {repeat_count}→2, gsap.to {to_count}→5")
        return True
    return False


def run_hyperframes_render(project_dir: str, output_path: str) -> bool:
    """运行HyperFrames渲染（分段渲染+拼接，避免Set maximum size exceeded）"""
    import re
    import json
    import tempfile
    import shutil
    
    print(f"  [video-renderer] 渲染: {project_dir}")
    
    # 读取index.html解析所有composition clips
    index_path = Path(project_dir) / "index.html"
    index_content = index_path.read_text(encoding="utf-8")
    
    # 解析所有clip信息: data-composition-id, data-composition-src, data-duration
    # 只匹配class="clip"的div（子composition），不匹配根div
    clip_pattern = r'class="clip".*?data-composition-id="([^"]+)".*?data-composition-src="(compositions/[^"]+)".*?data-duration="([^"]+)"'
    clips = re.findall(clip_pattern, index_content, re.DOTALL)
    
    if not clips:
        print(f"  ❌ [video-renderer] index.html中没有找到composition clips")
        return False
    
    print(f"  [video-renderer] 发现 {len(clips)} 个composition，分段渲染...")
    
    # 创建临时目录存放分段视频
    temp_dir = Path(project_dir) / "_render_segments"
    temp_dir.mkdir(exist_ok=True)
    
    # 备份原index.html（在修改之前）
    original_index = Path(project_dir) / "index.html"
    backup_index = temp_dir / "index_backup.html"
    import shutil
    shutil.copy2(original_index, backup_index)
    print(f"  [video-renderer] 已备份原 index.html")
    
    segment_files = []
    concat_list = temp_dir / "concat.txt"
    
    # 渲染每个composition
    for i, (comp_id, clip_src, duration) in enumerate(clips):
        clip_path = str(temp_dir / f"segment_{i:02d}.mp4")
        print(f"  [video-renderer] [{i+1}/{len(clips)}] 渲染 {clip_src} (id: {comp_id}, duration: {duration}s)...")
        
        # 创建临时index.html，只引用这一个composition，使用正确的composition ID
        temp_index_content = f'''<!doctype html>
<html>
<body>
  <div id="root" data-composition-id="main" data-start="0"
       data-duration="{duration}" data-width="1920" data-height="1080">
      <div id="{comp_id}" class="clip"
           data-composition-id="{comp_id}"
           data-composition-src="{clip_src}"
           data-start="0.0"
           data-duration="{duration}"
           data-track-index="0"
           data-width="1920"
           data-height="1080">
      </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    const mainTl = gsap.timeline({{ paused: true }});
    window.__timelines = window.__timelines || {{}};
    window.__timelines["main"] = mainTl;
  </script>
</body>
</html>'''
        original_index.write_text(temp_index_content, encoding="utf-8")
        
        # 使用项目根目录渲染
        cmd = f'npx hyperframes render . --output "{clip_path}" --low-memory-mode --protocol-timeout 600000 --quality draft --workers 1 --no-browser-gpu'
        
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=project_dir, capture_output=True, text=True, timeout=300
            )
            
            if result.returncode == 0 and Path(clip_path).exists():
                segment_files.append(clip_path)
                print(f"  [video-renderer]   ✅ {clip_src} 渲染完成")
            else:
                # 重试1: 简化HTML中的GSAP动画后重试
                print(f"  ⚠️ [video-renderer]   {clip_src} 渲染失败(rc={result.returncode})，尝试简化GSAP后重试...")
                simplified = _simplify_composition_gsap(project_dir, clip_src)
                if simplified:
                    result2 = subprocess.run(
                        cmd, shell=True, cwd=project_dir, capture_output=True, text=True, timeout=300
                    )
                    if result2.returncode == 0 and Path(clip_path).exists():
                        segment_files.append(clip_path)
                        print(f"  [video-renderer]   ✅ {clip_src} 简化后渲染成功")
                        continue
                
                # 重试2: 用空白帧兜底（确保视频时长完整）
                print(f"  ⚠️ [video-renderer]   {clip_src} 两次重试都失败，使用空白帧兜底...")
                fallback_clip = _render_fallback_frame(temp_dir, i, duration, project_dir)
                if fallback_clip:
                    segment_files.append(fallback_clip)
                    print(f"  [video-renderer]   ⚠️ {clip_src} 使用空白帧替代")
                else:
                    print(f"  ❌ [video-renderer]   {clip_src} 无法生成兜底帧，跳过")
                if result.stderr:
                    for line in result.stderr.split('\n'):
                        if 'Set maximum' in line or 'failed' in line.lower() or 'Error' in line:
                            print(f"    {line.strip()[:200]}")
                continue
                
        except subprocess.TimeoutExpired:
            print(f"  ❌ [video-renderer]   {clip_src} 渲染超时（300s）")
            return False
        except Exception as e:
            print(f"  ❌ [video-renderer]   {clip_src} 渲染错误: {e}")
            return False
        finally:
            # 每次渲染后恢复原index.html
            shutil.copy2(backup_index, original_index)
    
    # 拼接所有分段视频
    print(f"  [video-renderer] 拼接 {len(segment_files)} 个分段...")
    
    # 恢复原index.html
    backup_index = temp_dir / "index_backup.html"
    if backup_index.exists():
        import shutil
        original_index = Path(project_dir) / "index.html"
        shutil.copy2(backup_index, original_index)
        print(f"  [video-renderer] 已恢复原 index.html")
    
    # 写入concat列表
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg in segment_files:
            f.write(f"file '{seg}'\n")
    
    # 使用ffmpeg拼接
    concat_cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_list}" -c copy "{output_path}"'
    try:
        result = subprocess.run(
            concat_cmd, shell=True, capture_output=True, text=True, timeout=120
        )
        
        if result.returncode == 0 and Path(output_path).exists():
            print(f"  [video-renderer] ✅ 拼接完成: {output_path}")
            # 清理临时文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            return True
        else:
            print(f"  ❌ [video-renderer] 拼接失败")
            if result.stderr:
                print(f"    stderr: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ❌ [video-renderer] 拼接超时（120s）")
        return False
    except Exception as e:
        print(f"  ❌ [video-renderer] 拼接错误: {e}")
        return False


def _render_fallback_frame(temp_dir: Path, index: int, duration: str, project_dir: str) -> str:
    """渲染一个纯色空白帧作为兜底（确保视频时长完整）"""
    import tempfile
    clip_path = str(temp_dir / f"segment_{index:02d}.mp4")
    
    # 用 ffmpeg 生成纯色视频
    cmd = f'ffmpeg -y -f lavfi -i "color=c=0x1a1a2e:s=1920x1080:d={duration}:r=30" -c:v libx264 -preset ultrafast -crf 28 -pix_fmt yuv420p "{clip_path}"'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and Path(clip_path).exists():
            return clip_path
    except Exception:
        pass
    return ""


def _validate_html_structure(project_dir: str) -> bool:
    """预检：验证所有 HTML 文件结构完整性"""
    import re
    comp_dir = Path(project_dir) / "compositions"
    if not comp_dir.exists():
        print(f"  ⚠️ [video-renderer] compositions 目录不存在")
        return False

    issues = 0
    for html_file in sorted(comp_dir.glob("beat-*.html")):
        content = html_file.read_text(encoding="utf-8")
        checks = [
            ("<!DOCTYPE html>" in content, "缺少 DOCTYPE"),
            ('data-composition-id=' in content, "缺少 data-composition-id"),
            ('data-width=' in content, "缺少 data-width"),
            ('data-height=' in content, "缺少 data-height"),
            ('window.__timelines' in content, "缺少 window.__timelines 注册"),
            ('gsap' in content.lower(), "缺少 GSAP 引用"),
            ('class="scene"' in content or 'class=\"scene\"' in content, "缺少 scene div"),
        ]
        for ok, msg in checks:
            if not ok:
                print(f"  ⚠️ [video-renderer] {html_file.name}: {msg}")
                issues += 1

    if issues > 0:
        print(f"  ⚠️ [video-renderer] 发现 {issues} 个结构问题，继续渲染...")
    else:
        print(f"  ✅ [video-renderer] HTML 结构校验通过")
    return True


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

    # 预检：HTML 结构校验
    _validate_html_structure(project_dir)

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
        "hf_project_dir": str(HF_PROJECT_DIR),
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  视频路径: {result.get('video_path')}")
    print(f"  时长: {result.get('video_duration')}")
