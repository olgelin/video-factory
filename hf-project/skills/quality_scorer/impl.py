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

    # V13: LLM 二次校验 — 代码评分后让 LLM 实际看 HTML
    _llm_review_available = False
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from llm_utils import call_llm
        _llm_review_available = True
    except ImportError:
        print(f"  [quality_scorer] llm_utils 不可用，跳过 LLM 二次校验")

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

    # V13: LLM 二次校验 — 采样审查（场景多时只查代表性样本，避免臃肿）
    llm_reviews = []
    if _llm_review_available:
        review_prompt = _load_llm_review_prompt()
        all_html_files = sorted(comp_dir.glob("beat-*.html"))
        all_html_files = [f for f in all_html_files if "outro" not in f.name and "intro" not in f.name]
        # 采样策略：≤10个场景全部审查，否则均匀采样最多5个
        if len(all_html_files) <= 10:
            sample_size = len(all_html_files)
        else:
            sample_size = min(5, len(all_html_files))
        step = max(1, len(all_html_files) // max(1, sample_size))
        sampled_files = all_html_files[::step][:sample_size]
        print(f"  [LLM审查] {len(all_html_files)} 个场景, 采样 {len(sampled_files)} 个进行 LLM 审查")
        for html_file in sampled_files:
            html = html_file.read_text(encoding="utf-8")
            sid = int(re.search(r'beat-(\d+)', html_file.name).group(1))
            try:
                verdict = _llm_review_html(call_llm, review_prompt, html, sid)
                llm_reviews.append(verdict)
                print(f"  [LLM审查] Scene {sid}: {verdict.get('total', '?')}/100 — {verdict.get('verdict', '?')[:60]}")
            except Exception as e:
                print(f"  [LLM审查] Scene {sid}: 调用失败 ({e})")
    else:
        print(f"  [quality_scorer] ⚠️ LLM 二次校验不可用，仅保留代码评分")

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

    # V13: 加入 LLM 审查结果
    if llm_reviews:
        llm_avg = sum(r.get("total", 0) for r in llm_reviews) / max(len(llm_reviews), 1)
        summary["llm_review"] = {
            "reviews": llm_reviews,
            "average_score": round(llm_avg, 1),
            "grade": _overall_grade(llm_avg),
        }
        print(f"  [LLM审查] 均分: {llm_avg:.1f}/100" + (f"  ⚠️ 与代码评分差距大" if abs(llm_avg - avg_score) > 15 else ""))

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


def _load_llm_review_prompt() -> str:
    """加载 LLM 审查 prompt。"""
    prompt_path = Path(__file__).parent.parent / "hf_builder" / "prompts" / "llm_review.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    # 兜底：内置简化版 prompt
    return """你是短视频视觉质量评审。评审这段 HTML 场景代码的画面质量。

评分维度（1-10）：色彩冲击力、动效活力、数据可视化、布局层次、整体印象。

输出 JSON：{"color_impact":N,"animation_vitality":N,"data_visual":N,"layout_depth":N,"overall_wow":N,"total":N,"verdict":"...","issues":[...],"highlights":[...]}
只输出 JSON。"""


def _llm_review_html(call_llm_fn, review_prompt: str, html: str, scene_id: int) -> dict:
    """调用 LLM 审查单个场景 HTML，返回评审结果。"""
    import json as _json
    # V13 fix: 包含动画脚本段，确保 LLM 看到 tl.from 动效代码
    html_head = html[:4000]  # 前4000字符（CSS/结构）
    # 找包含 tl.from 的 script 块（跳过 CDN 加载标签）
    script_blocks = list(re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL))
    tl_script = ""
    for block in script_blocks:
        if 'tl.from' in block.group(0) or 'gsap.from' in block.group(0):
            tl_script = block.group(0)[:3000]
            break
    if tl_script:
        html_snippet = html_head + '\n\n/* --- 动画脚本 --- */\n' + tl_script
    else:
        html_snippet = html[:6000]
    full_prompt = f"{review_prompt}\n\n## 场景 {scene_id}\n```html\n{html_snippet}\n```"
    
    raw = call_llm_fn(full_prompt, system_prompt="你是JSON输出机。只输出合法JSON，不要任何解释、前言、后缀、markdown标记。", max_tokens=3000)
    # V13 fix: 鲁棒 JSON 提取 — 找最外层花括号块
    result = _extract_json(raw)
    if result:
        result["scene_id"] = scene_id
        return result
    return {"scene_id": scene_id, "total": 0, "verdict": f"LLM 输出解析失败: {raw[:100]}", "issues": [], "highlights": []}


def _extract_json(raw: str) -> dict:
    """鲁棒 JSON 提取：找最外层花括号块，处理嵌套、markdown 代码块、和截断 JSON。"""
    import json as _json
    # 1. 去掉 markdown 代码块包裹
    raw = re.sub(r'```(?:json)?\s*', '', raw)
    raw = re.sub(r'```\s*$', '', raw)
    
    # 2. 找第一个 { 和匹配的 }
    start = raw.find('{')
    if start < 0:
        return None
    depth = 0
    end = -1
    for i in range(start, len(raw)):
        if raw[i] == '{':
            depth += 1
        elif raw[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    
    # 3. 完整 JSON → 直接解析
    if end > 0:
        json_str = raw[start:end]
        try:
            return _json.loads(json_str)
        except _json.JSONDecodeError:
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            try:
                return _json.loads(json_str)
            except _json.JSONDecodeError:
                pass
    
    # 4. 截断 JSON 容错：逐步尝试补 } 回退解析
    truncated = raw[start:].rstrip()
    # 策略 A：直接补 } （截断在最后一个值之后，如 "total":70）
    try:
        result = _json.loads(truncated + '}')
        if 'total' in result:
            return result
    except _json.JSONDecodeError:
        pass
    # 策略 B：去掉最后不完整片段再补 } （截断在中途，如 "total":7）
    # 从后往前找最后一个逗号或冒号，保留到那里
    for sep in (',', ':'):
        last = truncated.rfind(sep)
        if last > 0:
            try:
                result = _json.loads(truncated[:last] + '}')
                if 'total' in result:
                    return result
            except _json.JSONDecodeError:
                pass
    # 策略 C：回退到最后一个完整的键值对（从倒数第二个逗号截）
    commas = [i for i, c in enumerate(truncated) if c == ',']
    if len(commas) >= 1:
        try:
            result = _json.loads(truncated[:commas[-1]] + '}')
            if 'total' in result:
                return result
        except _json.JSONDecodeError:
            pass
    
    return None


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    ctx = {"project_root": str(Path(__file__).parent.parent.parent)}
    run(ctx)
