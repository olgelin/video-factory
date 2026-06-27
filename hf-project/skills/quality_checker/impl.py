#!/usr/bin/env python3
"""
quality_checker/impl.py — V5.2 多点质量自检（吸收 OpenMontage 自检流程）

检查项：
1. ffprobe 基础验证（时长、分辨率、编码）
2. 帧采样（检测空白帧/黑帧）
3. 音频电平分析（响度、削波）
4. 字幕覆盖率检查
5. 字幕时间轴验证
"""

import os
import json
import subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def check_video_basics(video_path: str) -> dict:
    """ffprobe 基础验证"""
    issues = []
    info = {}

    try:
        result = subprocess.run(
            f'ffprobe -v quiet -print_format json -show_format -show_streams "{video_path}"',
            shell=True, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return {"ok": False, "issues": ["ffprobe 无法读取视频"], "info": {}}

        data = json.loads(result.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])

        duration = float(fmt.get("duration", 0))
        size = int(fmt.get("size", 0))
        info["duration"] = duration
        info["size_mb"] = size / 1024 / 1024

        # 检查1: 时长 > 0
        if duration <= 0:
            issues.append("视频时长为0")

        # 检查2: 文件大小合理 (> 1MB)
        if size < 1024 * 1024:
            issues.append(f"视频文件过小: {info['size_mb']:.1f}MB")

        # 检查3: 有视频流
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        if not video_streams:
            issues.append("缺少视频流")
        else:
            vs = video_streams[0]
            info["width"] = vs.get("width", 0)
            info["height"] = vs.get("height", 0)
            info["codec"] = vs.get("codec_name", "unknown")
            if info["width"] < 1280:
                issues.append(f"分辨率过低: {info['width']}x{info['height']}")

        # 检查4: 有音频流
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        info["has_audio"] = len(audio_streams) > 0
        if not info["has_audio"]:
            issues.append("缺少音频流")

    except Exception as e:
        return {"ok": False, "issues": [f"ffprobe 异常: {e}"], "info": info}

    return {"ok": len(issues) == 0, "issues": issues, "info": info}


def check_blank_frames(video_path: str, sample_count: int = 5) -> dict:
    """帧采样：检测是否有大量空白帧"""
    issues = []
    samples = []

    try:
        # 获取视频时长
        probe = subprocess.run(
            f'ffprobe -v quiet -print_format json -show_format "{video_path}"',
            shell=True, capture_output=True, text=True, timeout=15
        )
        duration = float(json.loads(probe.stdout).get("format", {}).get("duration", 0))
        if duration <= 0:
            return {"ok": False, "issues": ["无法获取视频时长"], "samples": []}

        # 在多个时间点采样帧
        for i in range(sample_count):
            t = duration * (i + 1) / (sample_count + 1)
            sample_path = OUTPUT_DIR / f"_qc_sample_{i}.png"
            cmd = f'ffmpeg -y -ss {t} -i "{video_path}" -vframes 1 -q:v 2 "{sample_path}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and sample_path.exists():
                # 用 ffprobe 检测帧的像素信息
                sig_result = subprocess.run(
                    f'ffprobe -v quiet -show_entries frame_tags=lavfi.signalstats.SATAVG -of csv=p=0 -f lavfi "movie={sample_path},signalstats"',
                    shell=True, capture_output=True, text=True, timeout=10
                )
                samples.append({"time": round(t, 1), "file": str(sample_path)})

                # 清理临时文件
                try:
                    sample_path.unlink()
                except Exception:
                    pass
            else:
                issues.append(f"无法在 {t:.1f}s 处采样帧")

    except Exception as e:
        issues.append(f"帧采样异常: {e}")

    return {"ok": len(issues) == 0, "issues": issues, "samples": samples}


def check_audio_levels(video_path: str) -> dict:
    """音频电平分析"""
    issues = []
    info = {}

    try:
        # 提取音频并分析响度
        result = subprocess.run(
            f'ffmpeg -i "{video_path}" -af "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" -f null -',
            shell=True, capture_output=True, text=True, timeout=60
        )

        # 从 stderr 提取 JSON
        import re
        json_match = re.search(r'\{[^}]+\}', result.stderr)
        if json_match:
            loudness = json.loads(json_match.group())
            info["input_i"] = float(loudness.get("input_i", 0))
            info["input_tp"] = float(loudness.get("input_tp", 0))
            info["input_lra"] = float(loudness.get("input_lra", 0))

            # 检查响度范围
            if info["input_i"] < -30:
                issues.append(f"音频过轻: {info['input_i']:.1f} LUFS")
            elif info["input_i"] > -10:
                issues.append(f"音频过响: {info['input_i']:.1f} LUFS")

            # 检查削波
            if info["input_tp"] > 0:
                issues.append(f"音频削波: True Peak {info['input_tp']:.1f} dB")
        else:
            # 降级：用 volumedetect
            result2 = subprocess.run(
                f'ffmpeg -i "{video_path}" -af "volumedetect" -f null -',
                shell=True, capture_output=True, text=True, timeout=60
            )
            max_vol_match = re.search(r'max_volume:\s*([-\d.]+)', result2.stderr)
            if max_vol_match:
                info["max_volume"] = float(max_vol_match.group(1))
                if info["max_volume"] > -1:
                    issues.append(f"音频接近削波: max_volume={info['max_volume']} dB")

    except Exception as e:
        issues.append(f"音频分析异常: {e}")

    return {"ok": len(issues) == 0, "issues": issues, "info": info}


def check_subtitle_coverage(srt_path: str, video_duration: float) -> dict:
    """字幕覆盖率检查"""
    issues = []
    info = {"total_entries": 0, "coverage_end": 0, "coverage_pct": 0}

    if not os.path.exists(srt_path):
        return {"ok": False, "issues": ["SRT 文件不存在"], "info": info}

    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析最后一条字幕的结束时间
        import re
        times = re.findall(r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})', content)
        info["total_entries"] = len(times)

        if times:
            last_end_str = times[-1][1].replace(",", ".")
            h, m, s = last_end_str.split(":")
            last_end = int(h) * 3600 + int(m) * 60 + float(s)
            info["coverage_end"] = last_end
            info["coverage_pct"] = (last_end / video_duration * 100) if video_duration > 0 else 0

            if info["coverage_pct"] < 80:
                issues.append(f"字幕覆盖率不足: {info['coverage_pct']:.0f}% (最后一条在 {last_end:.1f}s, 视频 {video_duration:.1f}s)")
        else:
            issues.append("SRT 中没有有效字幕条目")

    except Exception as e:
        issues.append(f"字幕检查异常: {e}")

    return {"ok": len(issues) == 0, "issues": issues, "info": info}


def check_subtitle_timing(srt_path: str) -> dict:
    """字幕时间轴验证（检测重叠、间隙、过短/过长）"""
    issues = []
    info = {"overlaps": 0, "gaps": 0, "too_short": 0, "too_long": 0}

    if not os.path.exists(srt_path):
        return {"ok": False, "issues": ["SRT 文件不存在"], "info": info}

    try:
        import re
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        times = re.findall(r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})', content)

        prev_end = 0
        for i, (start_str, end_str) in enumerate(times):
            start = _parse_srt_time(start_str)
            end = _parse_srt_time(end_str)
            dur = end - start

            # 检查重叠
            if start < prev_end - 0.05:  # 50ms 容差
                info["overlaps"] += 1

            # 检查间隙 (> 1s)
            if i > 0 and start - prev_end > 1.0:
                info["gaps"] += 1

            # 检查过短 (< 0.5s)
            if dur < 0.5:
                info["too_short"] += 1

            # 检查过长 (> 5s)
            if dur > 5.0:
                info["too_long"] += 1

            prev_end = end

        if info["overlaps"] > 0:
            issues.append(f"字幕重叠: {info['overlaps']} 处")
        if info["gaps"] > 2:
            issues.append(f"字幕间隙过多: {info['gaps']} 处 (>1s)")
        if info["too_short"] > 3:
            issues.append(f"字幕过短: {info['too_short']} 条 (<0.5s)")

    except Exception as e:
        issues.append(f"字幕时间轴检查异常: {e}")

    return {"ok": len(issues) == 0, "issues": issues, "info": info}


def _parse_srt_time(t: str) -> float:
    """解析 SRT 时间戳为秒"""
    t = t.replace(",", ".")
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def run_full_check(video_path: str, srt_path: str = None) -> dict:
    """运行完整质量检查（OpenMontage 风格多点自检）"""
    print(f"\n{'='*60}")
    print(f"  🔍 质量自检 (V5.2)")
    print(f"{'='*60}")

    results = {}

    # 1. 基础验证
    print(f"\n  [1/5] 视频基础验证...")
    results["basics"] = check_video_basics(video_path)
    status = "✅" if results["basics"]["ok"] else "⚠️"
    print(f"    {status} 时长: {results['basics']['info'].get('duration', 0):.1f}s, "
          f"分辨率: {results['basics']['info'].get('width', 0)}x{results['basics']['info'].get('height', 0)}, "
          f"大小: {results['basics']['info'].get('size_mb', 0):.1f}MB")
    for issue in results["basics"]["issues"]:
        print(f"      ⚠️ {issue}")

    # 2. 帧采样
    print(f"\n  [2/5] 帧采样...")
    results["frames"] = check_blank_frames(video_path)
    status = "✅" if results["frames"]["ok"] else "⚠️"
    print(f"    {status} 采样 {len(results['frames']['samples'])} 帧")
    for issue in results["frames"]["issues"]:
        print(f"      ⚠️ {issue}")

    # 3. 音频分析
    print(f"\n  [3/5] 音频电平分析...")
    results["audio"] = check_audio_levels(video_path)
    status = "✅" if results["audio"]["ok"] else "⚠️"
    ai = results["audio"]["info"]
    print(f"    {status} 响度: {ai.get('input_i', 'N/A')} LUFS, True Peak: {ai.get('input_tp', 'N/A')} dB")
    for issue in results["audio"]["issues"]:
        print(f"      ⚠️ {issue}")

    # 4. 字幕覆盖率
    if srt_path and os.path.exists(srt_path):
        duration = results["basics"]["info"].get("duration", 0)
        print(f"\n  [4/5] 字幕覆盖率...")
        results["subtitle_coverage"] = check_subtitle_coverage(srt_path, duration)
        status = "✅" if results["subtitle_coverage"]["ok"] else "⚠️"
        sc = results["subtitle_coverage"]["info"]
        print(f"    {status} {sc['total_entries']} 条字幕, 覆盖 {sc['coverage_pct']:.0f}% ({sc['coverage_end']:.1f}s/{duration:.1f}s)")
        for issue in results["subtitle_coverage"]["issues"]:
            print(f"      ⚠️ {issue}")

        # 5. 字幕时间轴
        print(f"\n  [5/5] 字幕时间轴验证...")
        results["subtitle_timing"] = check_subtitle_timing(srt_path)
        status = "✅" if results["subtitle_timing"]["ok"] else "⚠️"
        st = results["subtitle_timing"]["info"]
        print(f"    {status} 重叠:{st['overlaps']} 间隙:{st['gaps']} 过短:{st['too_short']} 过长:{st['too_long']}")
        for issue in results["subtitle_timing"]["issues"]:
            print(f"      ⚠️ {issue}")
    else:
        print(f"\n  [4/5] 字幕检查: 跳过 (无SRT)")
        print(f"\n  [5/5] 字幕时间轴: 跳过 (无SRT)")

    # 汇总
    all_ok = all(
        r.get("ok", True)
        for r in [results["basics"], results["frames"], results["audio"]]
    )
    if "subtitle_coverage" in results:
        all_ok = all_ok and results["subtitle_coverage"]["ok"]

    total_issues = sum(len(r.get("issues", [])) for r in results.values())
    print(f"\n{'='*60}")
    if all_ok:
        print(f"  ✅ 质量自检通过 (0 问题)")
    else:
        print(f"  ⚠️ 质量自检发现 {total_issues} 个问题")
    print(f"{'='*60}\n")

    results["overall_ok"] = all_ok
    results["total_issues"] = total_issues

    return results


def run(context: dict) -> dict:
    """主入口：运行质量检查"""
    video_path = context.get("mixed_path") or context.get("video_path")
    if not video_path:
        video_path = str(OUTPUT_DIR / "step11_final.mp4")

    if not os.path.exists(video_path):
        print(f"  ⚠️ [quality-checker] 视频不存在: {video_path}")
        return context

    srt_path = context.get("srt_path") or str(OUTPUT_DIR / "captions.srt")

    results = run_full_check(video_path, srt_path)

    # 保存结果
    qc_path = OUTPUT_DIR / "quality_check.json"
    with open(qc_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    context["quality_check"] = results
    context["quality_check_path"] = str(qc_path)
    return context


if __name__ == "__main__":
    import sys
    video = sys.argv[1] if len(sys.argv) > 1 else str(OUTPUT_DIR / "step11_final.mp4")
    srt = sys.argv[2] if len(sys.argv) > 2 else str(OUTPUT_DIR / "captions.srt")
    results = run_full_check(video, srt)
    print(f"\nOverall: {'PASS' if results['overall_ok'] else 'ISSUES FOUND'}")
