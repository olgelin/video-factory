"""
quality_scorer/impl.py — V5.3 逐场景质量评分
读取 hf_builder 产出的 HTML，用 motion_library 评分，生成汇总报告。
"""
import os
import json
import re
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def run(context: dict) -> dict:
    """主入口：评分所有场景 HTML"""
    project_root = Path(context.get("project_root", Path(__file__).parent.parent.parent))
    comp_dir = project_root / "hf_render_project" / "compositions"
    output_dir = project_root / "output"

    if not comp_dir.exists():
        print(f"  [quality_scorer] compositions 目录不存在: {comp_dir}")
        return context

    # 加载 motion_library
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "hf_builder"))
    try:
        from motion_library import score_scene_quality
    except ImportError:
        print(f"  [quality_scorer] motion_library 不可用，跳过评分")
        return context

    # 加载 storyboard
    sb_path = context.get("storyboard_path") or str(output_dir / "storyboard.json")
    scenes = []
    if os.path.exists(sb_path):
        with open(sb_path, "r", encoding="utf-8") as f:
            sb = json.load(f)
        scenes = sb if isinstance(sb, list) else sb.get("scenes", [])

    # 评分每个场景
    scores = []
    total_score = 0
    count = 0

    for html_file in sorted(comp_dir.glob("beat-*.html")):
        if "outro" in html_file.name or "intro" in html_file.name:
            continue

        html = html_file.read_text(encoding="utf-8")
        sid = int(re.search(r'beat-(\d+)', html_file.name).group(1))

        # 找对应 scene
        scene = {}
        if sid <= len(scenes):
            scene = scenes[sid - 1]

        result = score_scene_quality(html, scene)
        result["scene_id"] = sid
        result["file"] = html_file.name
        scores.append(result)
        total_score += result["total_score"]
        count += 1

        print(f"  [quality_scorer] Scene {sid}: {result['total_score']}/100 ({result['grade']})")

    # 汇总
    avg_score = total_score / max(count, 1)
    summary = {
        "version": "v5.3",
        "scene_count": count,
        "average_score": round(avg_score, 1),
        "grade": _overall_grade(avg_score),
        "per_scene": scores,
        "dimension_averages": _dimension_averages(scores),
    }

    # 保存
    scores_path = output_dir / "quality_scores.json"
    with open(scores_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"  [quality_scorer] ✅ 汇总: {avg_score:.1f}/100 ({summary['grade']})")
    print(f"  [quality_scorer] 报告: {scores_path}")

    context["quality_scores"] = summary
    context["quality_scores_path"] = str(scores_path)
    return context


def _overall_grade(score: float) -> str:
    if score >= 85:
        return "A — 优秀，可交付"
    elif score >= 70:
        return "B — 良好，建议微调"
    elif score >= 55:
        return "C — 合格，需关注弱项"
    elif score >= 40:
        return "D — 需改进，建议重渲染弱场景"
    else:
        return "F — 不合格，必须重渲染"


def _dimension_averages(scores: list) -> dict:
    """计算各维度平均分"""
    dims = ["visual_density", "data_visualization", "animation_quality",
            "color_harmony", "layout_structure", "typography"]
    avg = {}
    for dim in dims:
        vals = [s["dimensions"].get(dim, 0) for s in scores if "dimensions" in s]
        avg[dim] = round(sum(vals) / max(len(vals), 1), 1)
    return avg


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    ctx = {"project_root": str(Path(__file__).parent.parent.parent)}
    run(ctx)
