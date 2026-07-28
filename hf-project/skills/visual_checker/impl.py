"""
visual_checker/impl.py — V6 渲染后视觉校验
功能：从最终视频提取3-5帧，用LLM vision检查是否匹配原始话题意图
输出：output/visual_check.json
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
CHECK_RESULT_PATH = OUTPUT_DIR / "visual_check.json"


def _extract_frames(video_path: str, temp_dir: str, num_frames: int = 5) -> list[str]:
    """用 ffmpeg 从视频中均匀提取帧"""
    import subprocess as _sp

    # 获取视频时长
    result = _sp.run(
        f'ffprobe -v quiet -print_format json -show_format "{video_path}"',
        shell=True, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ❌ [visual-check] 无法读取视频信息")
        return []

    info = json.loads(result.stdout)
    duration = float(info.get("format", {}).get("duration", 0))
    if duration <= 0:
        print(f"  ❌ [visual-check] 视频时长为0")
        return []

    # 均匀选择时间点（跳过开头10%和结尾10%）
    start_pct = 0.10
    end_pct = 0.90
    usable_duration = duration * (end_pct - start_pct)
    start_offset = duration * start_pct

    frames = []
    for i in range(num_frames):
        t = start_offset + (usable_duration * i / max(num_frames - 1, 1))
        frame_path = os.path.join(temp_dir, f"frame_{i+1:02d}.jpg")
        cmd = (
            f'ffmpeg -y -ss {t:.2f} -i "{video_path}" '
            f'-vframes 1 -q:v 3 "{frame_path}"'
        )
        _sp.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if os.path.exists(frame_path):
            frames.append(frame_path)
            print(f"  [visual-check] 提取帧 {i+1}/{num_frames} @ {t:.1f}s")

    return frames


def _check_frame_with_vision(frame_path: str, topic: str) -> dict:
    """用 LLM vision 检查单帧是否匹配话题"""
    # 使用内部 vision 能力 — 将图片编码为 base64 并通过 provider 调用
    import base64
    import sys

    with open(frame_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    # 通过 provider 调用 vision model
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from provider import get_registry

    registry = get_registry()

    prompt = f"""Analyze this video frame and answer:
1. What is shown in this frame? (3-5 word description)
2. Does it visually relate to the topic: "{topic}"? (YES/NO)
3. Confidence: 0.0-1.0
4. Issues: list any visual problems (blank frame, off-topic, text errors, poor composition)

Respond in JSON:
{{"description":"...","matches_topic":true/false,"confidence":0.0,"issues":["..."]}}"""

    try:
        # Try vision-capable model first, fall back to text-only with image description
        result = registry.call_vision(
            prompt=prompt,
            image_path=frame_path,
            max_tokens=500,
            timeout=60,
        )
        if result:
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        print(f"    ⚠️ [visual-check] vision call failed: {e}")

    # Fallback: text-only analysis (no vision available)
    return {
        "description": "vision_unavailable",
        "matches_topic": None,
        "confidence": 0.0,
        "issues": ["vision_model_not_available"],
    }


def run(context: dict) -> dict:
    """主入口：提取帧 + LLM vision 检查"""
    topic = context.get("topic", "未知话题")
    print(f"  [visual-check] 检查视频是否匹配话题: '{topic}'")

    # 优先使用 upscaled 视频，其次 final 视频
    upscaled = context.get("upscaled_path") or str(OUTPUT_DIR / "step13_upscaled.mp4")
    final = context.get("mixed_path") or str(OUTPUT_DIR / "step11_final.mp4")

    video_path = upscaled if os.path.exists(upscaled) else final
    if not os.path.exists(video_path):
        # 尝试 step10 渲染输出
        video_path = context.get("video_path") or str(OUTPUT_DIR / "step10_video.mp4")

    if not os.path.exists(video_path):
        print(f"  ⚠️ [visual-check] 找不到视频文件，跳过")
        context["visual_check"] = {"error": "no_video_found", "frames_checked": 0}
        return context

    print(f"  [visual-check] 视频: {video_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        frames = _extract_frames(video_path, tmpdir, num_frames=5)
        if not frames:
            print(f"  ⚠️ [visual-check] 无法提取帧")
            context["visual_check"] = {"error": "frame_extraction_failed", "frames_checked": 0}
            return context

        results = []
        for fp in frames:
            r = _check_frame_with_vision(fp, topic)
            results.append({
                "frame": os.path.basename(fp),
                **r
            })

        # 汇总
        matches = [r.get("matches_topic") for r in results if r.get("matches_topic") is not None]
        confidences = [r.get("confidence", 0) for r in results]
        all_issues = []
        for r in results:
            all_issues.extend(r.get("issues", []))

        summary = {
            "topic": topic,
            "video_path": video_path,
            "frames_checked": len(results),
            "match_count": sum(1 for m in matches if m),
            "total_matches": len(matches),
            "avg_confidence": round(sum(confidences) / max(len(confidences), 1), 2),
            "verdict": "PASS" if (sum(1 for m in matches if m) >= max(len(matches) * 0.6, 1)) else "FAIL",
            "issues": all_issues,
            "per_frame": results,
        }

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(CHECK_RESULT_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"  [visual-check] 已保存: {CHECK_RESULT_PATH}")
        print(f"  [visual-check] 结果: {summary['verdict']} ({summary['match_count']}/{summary['total_matches']} 匹配, "
              f"置信度 {summary['avg_confidence']})")

        context["visual_check"] = summary
        context["visual_check_path"] = str(CHECK_RESULT_PATH)

    return context


if __name__ == "__main__":
    test_context = {
        "topic": "测试话题",
        "video_path": str(OUTPUT_DIR / "step10_video.mp4"),
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  结果: {result.get('visual_check', {}).get('verdict', 'N/A')}")
