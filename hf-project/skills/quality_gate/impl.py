#!/usr/bin/env python3
"""
quality_gate/impl.py — V6.0 统一质量关卡（合并 quality_scorer + quality_checker）

两阶段：
  1. HTML 阶段（hf_builder 之后）: 用 motion_library 逐场景评分
  2. 视频阶段（audio_mixer 之后）: ffprobe + 帧采样 + 音频 + 字幕

输出: output/quality_report.json
"""
import os, json, re, subprocess, sys
from pathlib import Path


def _overall_grade(score: float) -> str:
    if score >= 85: return "A — 优秀，可交付"
    elif score >= 70: return "B — 良好，建议微调"
    elif score >= 55: return "C — 合格，需关注弱项"
    elif score >= 40: return "D — 需改进"
    else: return "F — 不合格"


# ══════════════════════════════════════════════════════════
# Phase 1: HTML 评分
# ══════════════════════════════════════════════════════════

def score_html_scenes(project_root: Path, storyboard: list) -> dict:
    """逐场景 HTML 评分。"""
    comp_dir = project_root / "hf_render_project" / "compositions"
    if not comp_dir.exists():
        return {"error": "compositions 目录不存在", "scores": []}

    # 加载 motion_library
    lib_path = project_root / "skills" / "hf_builder"
    if str(lib_path) not in sys.path:
        sys.path.insert(0, str(lib_path))
    try:
        from motion_library import score_scene_quality
    except ImportError:
        return {"error": "motion_library 不可用", "scores": []}

    scores = []
    for html_file in sorted(comp_dir.glob("beat-*.html")):
        if "outro" in html_file.name or "intro" in html_file.name:
            continue
        html = html_file.read_text(encoding="utf-8")
        sid = int(re.search(r'beat-(\d+)', html_file.name).group(1))
        scene = storyboard[sid - 1] if sid <= len(storyboard) else {}
        result = score_scene_quality(html, scene)
        result["scene_id"] = sid
        result["file"] = html_file.name
        scores.append(result)
        print(f"  Scene {sid}: {result['total_score']}/100 ({result['grade']})")

    avg = sum(s["total_score"] for s in scores) / max(len(scores), 1)
    return {
        "average_score": round(avg, 1),
        "grade": _overall_grade(avg),
        "scene_count": len(scores),
        "per_scene": scores,
    }


# ══════════════════════════════════════════════════════════
# Phase 2: 视频质量检查
# ══════════════════════════════════════════════════════════

def _parse_srt_time(t: str) -> float:
    t = t.replace(",", ".")
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def check_video(video_path: str, srt_path: str = None) -> dict:
    """完整视频质量检查。"""
    results = {}
    issues_total = 0

    # 1. ffprobe 基础
    try:
        r = subprocess.run(
            f'ffprobe -v quiet -print_format json -show_format -show_streams "{video_path}"',
            shell=True, capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            fmt = data.get("format", {})
            streams = data.get("streams", [])
            duration = float(fmt.get("duration", 0))
            size_mb = int(fmt.get("size", 0)) / 1024 / 1024
            vs = [s for s in streams if s.get("codec_type") == "video"]
            has_audio = any(s.get("codec_type") == "audio" for s in streams)
            
            basics_issues = []
            if duration <= 0: basics_issues.append("时长为0")
            if size_mb < 1: basics_issues.append(f"文件过小: {size_mb:.1f}MB")
            if not vs: basics_issues.append("缺少视频流")
            if not has_audio: basics_issues.append("缺少音频流")
            
            results["basics"] = {
                "ok": len(basics_issues) == 0,
                "issues": basics_issues,
                "duration": duration, "size_mb": size_mb,
                "resolution": f"{vs[0].get('width',0)}x{vs[0].get('height',0)}" if vs else "N/A",
                "codec": vs[0].get("codec_name", "?") if vs else "?",
                "has_audio": has_audio,
            }
            issues_total += len(basics_issues)
            print(f"  [1/5] 基础: {duration:.1f}s, {size_mb:.1f}MB, {'✅' if not basics_issues else '⚠️ ' + str(basics_issues)}")
        else:
            results["basics"] = {"ok": False, "issues": ["ffprobe 失败"]}
            issues_total += 1
    except Exception as e:
        results["basics"] = {"ok": False, "issues": [str(e)]}
        issues_total += 1

    # 2. 帧采样（简化：只检查关键时间点帧是否存在）
    duration = results.get("basics", {}).get("duration", 0)
    if duration > 0:
        frame_issues = []
        for i in range(3):
            t = duration * (i + 1) / 4
            sample = Path(video_path).parent / f"_qc_{i}.png"
            r = subprocess.run(
                f'ffmpeg -y -ss {t} -i "{video_path}" -vframes 1 -q:v 2 "{sample}"',
                shell=True, capture_output=True, timeout=15
            )
            if r.returncode != 0 or not sample.exists():
                frame_issues.append(f"t={t:.1f}s 采样失败")
            try: sample.unlink()
            except: pass
        results["frames"] = {"ok": len(frame_issues) == 0, "issues": frame_issues, "sampled": 3}
        issues_total += len(frame_issues)
        print(f"  [2/5] 帧采样: {'✅' if not frame_issues else '⚠️'}")
    else:
        results["frames"] = {"ok": False, "issues": ["无法获取时长"]}
        issues_total += 1

    # 3. 音频
    try:
        r = subprocess.run(
            f'ffmpeg -i "{video_path}" -af "volumedetect" -f null -',
            shell=True, capture_output=True, text=True, timeout=30
        )
        max_vol = re.search(r'max_volume:\s*([-\d.]+)', r.stderr)
        mean_vol = re.search(r'mean_volume:\s*([-\d.]+)', r.stderr)
        audio_issues = []
        if max_vol:
            mv = float(max_vol.group(1))
            if mv > -1: audio_issues.append(f"接近削波: max={mv}dB")
        results["audio"] = {
            "ok": len(audio_issues) == 0,
            "issues": audio_issues,
            "max_volume": float(max_vol.group(1)) if max_vol else None,
            "mean_volume": float(mean_vol.group(1)) if mean_vol else None,
        }
        issues_total += len(audio_issues)
        print(f"  [3/5] 音频: {'✅' if not audio_issues else '⚠️ ' + str(audio_issues)}")
    except Exception as e:
        results["audio"] = {"ok": False, "issues": [str(e)]}
        issues_total += 1

    # 4+5. 字幕
    if srt_path and os.path.exists(srt_path):
        with open(srt_path, encoding="utf-8") as f:
            srt_text = f.read()
        times = re.findall(r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})', srt_text)
        
        srt_issues = []
        if times:
            last_end = _parse_srt_time(times[-1][1])
            coverage = (last_end / duration * 100) if duration > 0 else 0
            if coverage < 80: srt_issues.append(f"覆盖率 {coverage:.0f}%")
            
            # 时间轴
            overlaps = gaps = 0
            prev_end = 0
            for start_str, end_str in times:
                s = _parse_srt_time(start_str); e = _parse_srt_time(end_str)
                if s < prev_end - 0.05: overlaps += 1
                if s - prev_end > 1.0: gaps += 1
                prev_end = e
            
            results["subtitle"] = {
                "ok": len(srt_issues) == 0,
                "issues": srt_issues,
                "entries": len(times), "coverage_pct": round(coverage, 1),
                "overlaps": overlaps, "gaps": gaps,
            }
            issues_total += len(srt_issues)
        else:
            results["subtitle"] = {"ok": False, "issues": ["无有效字幕"], "entries": 0}
            issues_total += 1
        print(f"  [4-5/5] 字幕: {len(times)}条, {'✅' if not srt_issues else '⚠️ ' + str(srt_issues)}")
    else:
        results["subtitle"] = {"ok": True, "issues": [], "entries": 0, "skipped": True}
        print(f"  [4-5/5] 字幕: 跳过")

    return {
        "overall_ok": issues_total == 0,
        "total_issues": issues_total,
        "checks": results,
    }


# ══════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════

def run(context: dict) -> dict:
    """统一质量关卡。自动检测当前阶段。"""
    project_root = Path(context.get("project_root",
        Path(__file__).parent.parent.parent))
    output_dir = project_root / "output"

    report = {"version": "v6.0", "phases": {}}

    # ── Phase 1: HTML 评分 ──
    comp_dir = project_root / "hf_render_project" / "compositions"
    if comp_dir.exists() and list(comp_dir.glob("beat-*.html")):
        sb_path = context.get("storyboard_path") or str(output_dir / "storyboard.json")
        storyboard = []
        if os.path.exists(sb_path):
            with open(sb_path, encoding="utf-8") as f:
                sb = json.load(f)
            storyboard = sb if isinstance(sb, list) else sb.get("scenes", [])
        
        print(f"\n{'='*50}")
        print(f"  🎯 Phase 1: HTML 场景评分")
        print(f"{'='*50}")
        report["html_scores"] = score_html_scenes(project_root, storyboard)
        hs = report["html_scores"]
        if "average_score" in hs:
            print(f"  平均: {hs['average_score']}/100 ({hs['grade']})")

    # ── Phase 2: 视频质量 ──
    video_path = context.get("mixed_path") or str(output_dir / "step11_final.mp4")
    if os.path.exists(video_path):
        srt_path = context.get("srt_path") or str(output_dir / "captions.srt")
        
        print(f"\n{'='*50}")
        print(f"  🔍 Phase 2: 视频质量检查")
        print(f"{'='*50}")
        report["video_check"] = check_video(video_path, srt_path if os.path.exists(srt_path) else None)
        vc = report["video_check"]
        status = "✅ PASS" if vc["overall_ok"] else f"⚠️ {vc['total_issues']} issues"
        print(f"  结果: {status}")

    # 保存
    out_path = output_dir / "quality_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    context["quality_report"] = report
    context["quality_report_path"] = str(out_path)
    return context


if __name__ == "__main__":
    ctx = {"project_root": str(Path(__file__).parent.parent.parent)}
    run(ctx)
    print("\n✅ quality_gate 测试完成")
