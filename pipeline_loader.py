#!/usr/bin/env python3
"""
pipeline_loader.py — YAML驱动的Pipeline加载与执行引擎

从 pipeline_defs/*.yaml 加载 pipeline 定义，按 phase 分组执行：
- 同一 phase 内 parallel_group 相同的 stage 并行执行
- 不同 phase 之间串行
- 支持 critical check、retry、timeout、rate limiting
"""

import os
import sys
import json
import time
import threading
import traceback
from pathlib import Path
from typing import Any, Optional

import yaml

# 路径
WORKSPACE = Path(__file__).parent
HF_PROJECT = WORKSPACE / "hf-project"
SKILLS_DIR = HF_PROJECT / "skills"
OUTPUT_DIR = HF_PROJECT / "output"
PIPELINE_DEFS_DIR = WORKSPACE / "pipeline_defs"

sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(HF_PROJECT))


def load_pipeline(name: str) -> dict:
    """加载 pipeline YAML 定义"""
    path = PIPELINE_DEFS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Pipeline 定义不存在: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_pipelines() -> list[str]:
    """列出所有可用 pipeline"""
    return [p.stem for p in PIPELINE_DEFS_DIR.glob("*.yaml")]


def load_skill(skill_name: str):
    """动态加载 skill 模块"""
    import importlib.util
    skill_path = SKILLS_DIR / skill_name / "impl.py"
    if not skill_path.exists():
        print(f"  ⚠️ Skill 不存在: {skill_name} ({skill_path})")
        return None
    spec = importlib.util.spec_from_file_location(skill_name, skill_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check_critical(manifest: dict, stage_name: str, context: dict) -> bool:
    """检查关键步骤是否产出预期文件"""
    checks = manifest.get("critical_checks", {})
    if stage_name not in checks:
        return True
    pattern = checks[stage_name]
    base = HF_PROJECT
    if "*" in pattern:
        import glob as _glob
        matches = _glob.glob(str(base / pattern))
        return len(matches) > 0
    return (base / pattern).exists()


def run_stage(
    manifest: dict,
    stage: dict,
    context: dict,
    cost_tracker=None,
) -> dict:
    """执行单个 stage"""
    name = stage["name"]
    skill_name = stage["skill"]
    step = stage.get("step", 0)
    timeout = stage.get("timeout", 300)
    max_retry = stage.get("retry", 0)
    critical = stage.get("critical", False)
    rate_limit = stage.get("rate_limit", {})

    print(f"\n{'='*60}")
    print(f"[Step {step}] {name} — {stage.get('description', '')}")
    print(f"{'='*60}")

    module = load_skill(skill_name)
    if not module or not hasattr(module, "run"):
        print(f"  ⚠️ 跳过 {name}（无 run() 方法）")
        return context

    # Rate limiting: delay between calls
    delay = rate_limit.get("delay_between_calls", 0)
    if delay > 0:
        print(f"  [rate-limit] 等待 {delay}s...")
        time.sleep(delay)

    for attempt in range(max_retry + 1):
        try:
            if cost_tracker:
                cost_tracker.estimate(stage_name=name, provider=stage.get("provider", "unknown"))

            result = module.run(context)

            if cost_tracker:
                cost_tracker.reconcile(stage_name=name, success=True)

            # Critical check
            if critical and not _check_critical(manifest, name, result):
                print(f"  🛑 关键步骤 {name} 未产出预期文件")
                if attempt < max_retry:
                    print(f"  🔄 重试 {attempt + 2}/{max_retry + 1}...")
                    continue
                raise RuntimeError(f"关键步骤 {name} 未产出预期文件")

            print(f"  ✅ {name} 完成")
            return result

        except Exception as e:
            if cost_tracker:
                cost_tracker.reconcile(stage_name=name, success=False)
            print(f"  ❌ {name} 失败: {e}")
            traceback.print_exc()
            if attempt < max_retry:
                wait = (attempt + 1) * 3
                print(f"  🔄 重试 {attempt + 2}/{max_retry + 1}（等待 {wait}s）...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"步骤 {name} 失败（已重试 {max_retry} 次）: {e}") from e

    return context


def run_parallel_stages(
    manifest: dict,
    stages: list[dict],
    context: dict,
    cost_tracker=None,
) -> dict:
    """并行执行多个 stage"""
    results = {}
    errors = []
    lock = threading.Lock()

    def worker(stage: dict):
        try:
            ctx = run_stage(manifest, stage, context, cost_tracker)
            with lock:
                results[stage["name"]] = ctx
        except Exception as e:
            with lock:
                errors.append((stage["name"], e))

    threads = []
    for stage in stages:
        t = threading.Thread(target=worker, args=(stage,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    if errors:
        for name, e in errors:
            print(f"  ❌ {name} 并行执行失败: {e}")
        raise RuntimeError(f"{len(errors)} 个并行步骤失败")

    # 合并 context（后面的覆盖前面的）
    merged = dict(context)
    for ctx in results.values():
        merged.update(ctx)
    return merged


def run_pipeline(
    pipeline_name: str = "short_video",
    topic: str = None,
    script: str = None,
    steps: str = "1-13",
    skip_voice: bool = False,
    skip_bgm: bool = False,
    vertical: bool = False,
    no_feedback: bool = False,
    cost_tracker=None,
) -> dict:
    """
    执行完整 pipeline

    Args:
        pipeline_name: pipeline 定义文件名（不含 .yaml）
        topic: 指定话题（跳过选题步骤）
        script: 指定文案（跳过选题+剧本步骤）
        steps: 步骤范围，如 "1-13"
        skip_voice: 跳过配音
        skip_bgm: 跳过 BGM
        vertical: 竖屏模式
        no_feedback: 禁用反馈系统
        cost_tracker: 成本追踪器实例

    Returns:
        最终 context dict
    """
    manifest = load_pipeline(pipeline_name)

    # 解析步骤范围
    parts = steps.split("-")
    start_step = int(parts[0])
    end_step = int(parts[1]) if len(parts) > 1 else start_step

    # 视频分辨率
    video_width, video_height = (1080, 1920) if vertical else (1920, 1080)

    print(f"\n{'='*60}")
    print(f"🎬 {manifest.get('description', pipeline_name)}")
    print(f"{'='*60}")
    print(f"Pipeline: {pipeline_name} v{manifest.get('version', '?')}")
    print(f"话题: {topic or '自动选题'}")
    print(f"步骤: {start_step}-{end_step}")
    print(f"分辨率: {video_width}x{video_height}")
    print(f"{'='*60}")

    # 初始化 context
    context = {
        "topic": topic,
        "output_dir": str(OUTPUT_DIR),
        "project_root": str(HF_PROJECT),
        "voice_path": str(OUTPUT_DIR / "step05_voice.wav"),
        "bgm_path": str(OUTPUT_DIR / "bgm.wav"),
        "video_path": str(OUTPUT_DIR / "step10_video.mp4"),
        "video_width": video_width,
        "video_height": video_height,
    }

    # 加载已保存的 context
    saved_ctx_path = OUTPUT_DIR / "pipeline_context.json"
    if saved_ctx_path.exists():
        try:
            with open(saved_ctx_path, encoding="utf-8") as f:
                saved_ctx = json.load(f)
            for k, v in saved_ctx.items():
                if k not in context or context[k] is None:
                    context[k] = v
        except Exception:
            pass

    # 补全 topic
    if not context.get("topic"):
        topic_file = OUTPUT_DIR / "topic_selected.json"
        if topic_file.exists():
            try:
                with open(topic_file, encoding="utf-8") as f:
                    td = json.load(f)
                context["topic"] = td.get("selected_topic") or td.get("topic", "")
            except Exception:
                pass

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 处理 --topic（跳过选题）
    if topic:
        topic_file = OUTPUT_DIR / "topic_selected.json"
        topic_data = {
            "selected_topic": topic,
            "topic": topic,
            "angle": f"深度解析: {topic}",
            "hook": f"你绝对想不到，{topic}",
            "key_points": [
                {"point": "核心数据和背景", "data": ""},
                {"point": "关键影响和意义", "data": ""},
                {"point": "未来趋势和展望", "data": ""},
            ],
            "target_audience": "关注时事的网民",
            "sources": [],
            "score": {"total": 55, "max": 60},
        }
        topic_file.write_text(json.dumps(topic_data, ensure_ascii=False, indent=2))

    # 处理 --script（跳过选题+剧本）
    if script:
        script_path = Path(script)
        if script_path.exists():
            script_text = script_path.read_text(encoding="utf-8").strip()
        else:
            script_text = script.strip()

        paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in script_text.split("\n") if p.strip()]

        sections = [
            {"section_id": i, "content": p, "talking_point": f"段落{i}"}
            for i, p in enumerate(paragraphs, 1)
        ]

        script_data = {
            "topic": topic or paragraphs[0][:20],
            "mood": "自然",
            "voiceover_sections": sections,
            "total_chars": sum(len(s["content"]) for s in sections),
        }
        (OUTPUT_DIR / "step03_script.json").write_text(
            json.dumps(script_data, ensure_ascii=False, indent=2)
        )

    # 按 phase 分组
    stages = manifest.get("stages", [])
    phase_groups: dict[str, list[dict]] = {}
    for stage in stages:
        step = stage.get("step", 0)
        if step < start_step or step > end_step:
            continue
        # Skip flags
        if topic and stage["name"] in ("topic_scout", "topic_selector"):
            continue
        if script and stage["name"] in ("topic_scout", "topic_selector", "script_writer"):
            continue
        if skip_voice and stage["name"] == "voice_gen":
            continue
        if skip_bgm and stage["name"] in ("lyrics_writer", "bgm_generator"):
            continue

        phase = str(stage.get("phase", "1"))
        if phase not in phase_groups:
            phase_groups[phase] = []
        phase_groups[phase].append(stage)

    # 按 phase 顺序执行
    for phase in sorted(phase_groups.keys(), key=lambda x: float(x)):
        phase_stages = phase_groups[phase]
        parallel_groups: dict[str, list[dict]] = {}

        for stage in phase_stages:
            pg = stage.get("parallel_group") or f"_serial_{stage['name']}"
            if pg not in parallel_groups:
                parallel_groups[pg] = []
            parallel_groups[pg].append(stage)

        # 不同 parallel_group 之间串行，同组内并行
        for pg_name, pg_stages in parallel_groups.items():
            if len(pg_stages) == 1:
                context = run_stage(manifest, pg_stages[0], context, cost_tracker)
            else:
                print(f"\n⚡ 并行执行: {', '.join(s['name'] for s in pg_stages)}")
                context = run_parallel_stages(manifest, pg_stages, context, cost_tracker)

    # 保存 context
    context_path = OUTPUT_DIR / "pipeline_context.json"
    with open(context_path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"✅ Pipeline 完成!")
    print(f"{'='*60}")
    print(f"最终视频: {context.get('mixed_path', OUTPUT_DIR / 'step11_final.mp4')}")
    print(f"配音: {context.get('voice_path', 'N/A')}")
    print(f"BGM: {context.get('bgm_path', 'N/A')}")
    print(f"Context: {context_path}")

    if cost_tracker:
        snapshot = cost_tracker.snapshot()
        print(f"💰 费用: ${snapshot.get('total_spent_usd', 0):.4f}")

    return context


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="短视频工厂 — YAML驱动Pipeline")
    parser.add_argument("--pipeline", default="short_video", help="Pipeline 名称")
    parser.add_argument("--topic", help="视频话题")
    parser.add_argument("--script", help="直接提供文案")
    parser.add_argument("--skip-voice", action="store_true", help="跳过配音")
    parser.add_argument("--skip-bgm", action="store_true", help="跳过BGM")
    parser.add_argument("--steps", default="1-13", help="步骤范围")
    parser.add_argument("--vertical", action="store_true", help="竖屏模式")
    parser.add_argument("--no-feedback", action="store_true", help="禁用反馈系统")
    parser.add_argument("--list", action="store_true", help="列出所有 pipeline")
    args = parser.parse_args()

    if args.list:
        print("可用 Pipelines:")
        for p in list_pipelines():
            manifest = load_pipeline(p)
            print(f"  {p}: {manifest.get('description', '')}")
        sys.exit(0)

    run_pipeline(
        pipeline_name=args.pipeline,
        topic=args.topic,
        script=args.script,
        steps=args.steps,
        skip_voice=args.skip_voice,
        skip_bgm=args.skip_bgm,
        vertical=args.vertical,
        no_feedback=args.no_feedback,
    )
