#!/usr/bin/env python3
"""
短视频工厂 — 完整Pipeline
14步流程：选题 → 剧本 → 歌词 → 配音 → BGM → 分镜 → 设计 → 渲染 → 混合
"""

import os
import sys
import json
import importlib.util
from pathlib import Path
from datetime import datetime

# === 根本修复：清除PYTHONPATH防止hermes-agent/venv覆盖core/venv ===
# Hermes Agent运行时会设置PYTHONPATH指向hermes-agent/venv（cp311包）
# 这导致transformers/tokenizers等从错误的venv加载，引发版本冲突
# 1. 删除环境变量（防止子进程继承）
# 2. 从sys.path移除已注入的hermes-agent路径（当前进程已生效）
if 'PYTHONPATH' in os.environ:
    del os.environ['PYTHONPATH']
# 过滤所有hermes-agent/hermes_agent相关路径（连字符和下划线两种形式）
sys.path[:] = [p for p in sys.path if not any(x in p.lower() for x in ['hermes-agent', 'hermes_agent']) or 'core' in p.lower()]

import platform
if platform.system() == 'Windows':
    _hermes_home = Path(os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes')))
    # Hermes安装目录 = HERMES_HOME的父目录（E:\Hermes-Agent）
    _core_site = _hermes_home / 'core' / 'venv' / 'Lib' / 'site-packages'
else:
    _core_site = Path('/e/Hermes-Agent/core/venv/lib') / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
if _core_site.exists() and str(_core_site) not in sys.path:
    sys.path.insert(0, str(_core_site))

# 加载.env文件
def load_env():
    """从.env文件加载环境变量"""
    env_files = [
        Path(__file__).parent / ".env",
        Path(__file__).parent / "video-factory-clawhub" / ".env",
    ]
    for env_file in env_files:
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
            print(f"  [env] 已加载: {env_file}")
            return
    print(f"  ⚠️ [env] 未找到.env文件")

load_env()

# 路径设置
WORKSPACE = Path(__file__).parent
HF_PROJECT = WORKSPACE / "hf-project"
SKILLS_DIR = HF_PROJECT / "skills"
OUTPUT_DIR = HF_PROJECT / "output"
FEEDBACK_DIR = WORKSPACE / "feedback_system"

sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(FEEDBACK_DIR))

# 导入反馈系统
try:
    from quality_tracker import trace_failure, check_skill_quality
    from auto_optimizer import optimize_skill, get_optimization_hints, should_retry
    from dependency_manager import check_updates, update_all
    FEEDBACK_ENABLED = True
except ImportError as e:
    print(f"  ⚠️ 反馈系统导入失败: {e}")
    FEEDBACK_ENABLED = False

def load_skill(skill_name: str):
    """动态加载skill模块"""
    skill_path = SKILLS_DIR / skill_name / "impl.py"
    if not skill_path.exists():
        print(f"  ⚠️ Skill不存在: {skill_name} ({skill_path})")
        return None
    spec = importlib.util.spec_from_file_location(skill_name, skill_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# 关键步骤：失败时必须产出文件，否则终止pipeline
CRITICAL_CHECKS = {
    "script_writer": lambda ctx: (OUTPUT_DIR / "step03_script.json").exists(),
    "voice_gen": lambda ctx: (OUTPUT_DIR / "step05_voice.wav").exists(),
    "hf_builder": lambda ctx: (HF_PROJECT / "hf_render_project" / "compositions").exists() and any((HF_PROJECT / "hf_render_project" / "compositions").glob("beat-*.html")),
    "video_renderer": lambda ctx: (OUTPUT_DIR / "step10_video.mp4").exists(),
    "audio_mixer": lambda ctx: (OUTPUT_DIR / "step11_final.mp4").exists(),
}

def run_step(skill_name: str, context: dict, step_num: int) -> dict:
    """执行单个skill步骤"""
    print(f"\n{'='*60}")
    print(f"[Step {step_num}] {skill_name}")
    print(f"{'='*60}")
    
    module = load_skill(skill_name)
    if not module or not hasattr(module, 'run'):
        print(f"  ⚠️ 跳过 {skill_name}")
        return context
    
    try:
        context = module.run(context)
        print(f"  ✅ {skill_name} 完成")
    except Exception as e:
        print(f"  ❌ {skill_name} 失败: {e}")
        import traceback
        traceback.print_exc()
        print(f"  🛑 步骤 {skill_name} 异常终止")
        raise RuntimeError(f"步骤 {skill_name} 失败: {e}") from e
    

    # 关键步骤产出检查
    if skill_name in CRITICAL_CHECKS:
        if not CRITICAL_CHECKS[skill_name](context):
            print("  🛑 关键步骤 " + skill_name + " 未产出预期文件")
            raise RuntimeError(f"关键步骤 {skill_name} 未产出预期文件")

    return context

def check_skill_quality_after_step(skill_name: str, context: dict):
    """执行skill后检查质量"""
    try:
        if skill_name == "script_writer":
            script_data = context.get("script_data")
            if script_data:
                score, issues = check_skill_quality("script", script_data)
                if issues:
                    print(f"  ⚠️ 脚本质量问题: {issues}")
                    # 尝试优化
                    if should_retry("script_writer", 1, {"issues": [{"skill": "script_writer", "issues": issues}]}):
                        optimization = optimize_skill("script_writer", {"issues": [{"skill": "script_writer", "issues": issues}]})
                        if optimization:
                            print(f"  💡 优化建议已生成")
        
        elif skill_name == "voice_gen":
            voice_path = context.get("voice_path")
            if voice_path:
                score, issues = check_skill_quality("voice", voice_path)
                if issues:
                    print(f"  ⚠️ 配音质量问题: {issues}")
        
        elif skill_name == "bgm_generator":
            bgm_path = context.get("bgm_path")
            if bgm_path:
                score, issues = check_skill_quality("bgm", bgm_path)
                if issues:
                    print(f"  ⚠️ BGM质量问题: {issues}")
        
        elif skill_name == "storyboard":
            storyboard_data = context.get("storyboard_data")
            if storyboard_data:
                score, issues = check_skill_quality("storyboard", storyboard_data)
                if issues:
                    print(f"  ⚠️ Storyboard质量问题: {issues}")
        
        elif skill_name == "hf_builder":
            # 检查所有生成的HTML
            compositions_dir = HF_PROJECT / "hf_render_project" / "compositions"
            if compositions_dir.exists():
                for html_file in sorted(compositions_dir.glob("beat-*.html")):
                    if html_file.name == "beat-outro.html":
                        continue
                    html_content = html_file.read_text(encoding="utf-8")
                    score, issues = check_skill_quality("html", html_content)
                    if issues:
                        print(f"  ⚠️ {html_file.name} 质量问题: {issues}")
    except Exception as e:
        print(f"  ⚠️ 质量检查失败: {e}")

def main():
    global FEEDBACK_ENABLED
    import argparse
    parser = argparse.ArgumentParser(description="短视频工厂 — 完整Pipeline")
    parser.add_argument("--topic", type=str, help="视频话题")
    parser.add_argument("--script", type=str, help="直接提供文案（文件路径或内联文本），跳过选题+剧本生成")
    parser.add_argument("--skip-voice", action="store_true", help="跳过配音生成")
    parser.add_argument("--skip-bgm", action="store_true", help="跳过BGM生成")
    parser.add_argument("--steps", type=str, default="1-12", help="执行步骤范围 (如 1-12)")
    parser.add_argument("--check-deps", action="store_true", help="检查依赖更新")
    parser.add_argument("--update-deps", action="store_true", help="更新所有依赖")
    parser.add_argument("--no-feedback", action="store_true", help="禁用反馈系统")
    parser.add_argument("--vertical", action="store_true", help="竖屏模式 (1080x1920)")
    args = parser.parse_args()
    
    # 视频分辨率
    if args.vertical:
        video_width, video_height = 1080, 1920
    else:
        video_width, video_height = 1920, 1080
    
    # 依赖检查
    if args.check_deps:
        if not FEEDBACK_ENABLED:
            print("  ⚠️ 反馈系统未启用，无法检查依赖更新")
            return
        print("\n" + "="*60)
        print("📦 检查依赖更新")
        print("="*60)
        updates = check_updates()
        if updates:
            print(f"\n发现 {len(updates)} 个更新:")
            for u in updates:
                print(f"  - {u['name']}: {u['installed']} → {u['latest']}")
        else:
            print("\n所有依赖都是最新版本")
        return
    
    # 依赖更新
    if args.update_deps:
        if not FEEDBACK_ENABLED:
            print("  ⚠️ 反馈系统未启用，无法更新依赖")
            return
        print("\n" + "="*60)
        print("🔄 更新所有依赖")
        print("="*60)
        results = update_all()
        if results:
            print("\n更新结果:")
            for r in results:
                print(f"  - {r['name']}: {r['status']}")
        return
    
    # 解析步骤范围
    try:
        parts = args.steps.split("-")
        if len(parts) == 1:
            start_step = end_step = int(parts[0])
        elif len(parts) == 2:
            start_step, end_step = int(parts[0]), int(parts[1])
        else:
            raise ValueError
        if not (1 <= start_step <= end_step <= 12):
            print(f"  ❌ 步骤范围必须在1-12之间: {args.steps}")
            sys.exit(1)
    except (ValueError, IndexError):
        print(f"  ❌ --steps格式错误: {args.steps}，应为 N 或 N-M (如 1-12)")
        sys.exit(1)
    
    # 反馈系统开关
    if args.no_feedback:
        FEEDBACK_ENABLED = False
        print(f"  ⚠️ 反馈系统已禁用")
    
    print(f"\n{'='*60}")
    print(f"🎬 短视频工厂 — 完整Pipeline")
    print(f"{'='*60}")
    print(f"话题: {args.topic}")
    print(f"步骤: {start_step}-{end_step}")
    print(f"反馈系统: {'启用' if FEEDBACK_ENABLED else '禁用'}")
    print(f"输出: {OUTPUT_DIR}")
    print(f"{'='*60}")
    
    # 完整运行(从step1开始)时清理旧输出，防止stale file被下游读取
    if start_step == 1:
        import shutil
        stale_files = [
            OUTPUT_DIR / "step03_script.json",
            OUTPUT_DIR / "step05_voice.wav",
            OUTPUT_DIR / "step10_video.mp4",
            OUTPUT_DIR / "step11_final.mp4",
            OUTPUT_DIR / "bgm.wav",
            OUTPUT_DIR / "mixed_audio.wav",
            OUTPUT_DIR / "normalized_voice.wav",
            OUTPUT_DIR / "captions.srt",
            OUTPUT_DIR / "whisperx_transcript.json",
            OUTPUT_DIR / "storyboard.json",
            OUTPUT_DIR / "design.md",
            OUTPUT_DIR / "lyrics.txt",
            OUTPUT_DIR / "metadata.json",
            OUTPUT_DIR / "pipeline_context.json",
            OUTPUT_DIR / "voice_scene_durations.json",
        ]
        for f in stale_files:
            if f.exists():
                f.unlink()
        # 清理渲染场景目录
        scenes_dir = HF_PROJECT / "hf_render_project" / "scenes"
        if scenes_dir.exists():
            shutil.rmtree(scenes_dir)
        compositions_dir = HF_PROJECT / "hf_render_project" / "compositions"
        if compositions_dir.exists():
            shutil.rmtree(compositions_dir)
        print(f"  🧹 已清理旧输出文件（完整运行模式）")
    
    # 初始化context（如果有已保存的context，先加载以保留前序步骤的数据）
    context = {
        "topic": args.topic,
        "output_dir": str(OUTPUT_DIR),
        "project_root": str(HF_PROJECT),
        "voice_path": str(OUTPUT_DIR / "step05_voice.wav"),
        "bgm_path": str(OUTPUT_DIR / "bgm.wav"),
        "video_path": str(OUTPUT_DIR / "step10_video.mp4"),
        "video_width": video_width,
        "video_height": video_height,
    }
    
    # 加载已保存的context（保留前序步骤的数据，如voice_scene_durations）
    saved_context_path = OUTPUT_DIR / "pipeline_context.json"
    if saved_context_path.exists():
        try:
            with open(saved_context_path, "r", encoding="utf-8") as f:
                saved_ctx = json.load(f)
            # 合并：已保存的数据不覆盖显式设置的值
            for k, v in saved_ctx.items():
                if k not in context:
                    context[k] = v
            print(f"  [context] 已加载保存的context ({len(saved_ctx)} keys)")
        except Exception as e:
            print(f"  ⚠️ [context] 加载失败: {e}")
    
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 如果指定了 --topic，直接写入 topic_selected.json，跳过选题步骤
    topic_file = OUTPUT_DIR / "topic_selected.json"
    if args.topic:
        topic_data = {
            "selected_topic": args.topic,
            "topic": args.topic,
            "angle": f"深度解析: {args.topic}",
            "hook": f"你绝对想不到，{args.topic}",
            "key_points": [
                {"point": "核心数据和背景", "data": ""},
                {"point": "关键影响和意义", "data": ""},
                {"point": "未来趋势和展望", "data": ""}
            ],
            "target_audience": "科技爱好者、投资者、关注时事的网民",
            "sources": [],
            "score": {"total": 55, "max": 60}
        }
        topic_file.write_text(json.dumps(topic_data, ensure_ascii=False, indent=2))
        print(f"  [topic] 已指定话题，跳过选题: {args.topic}")
    
    # 如果指定了 --script，直接写入 step03_script.json，跳过选题+剧本生成
    script_file = OUTPUT_DIR / "step03_script.json"
    if args.script:
        # 读取文案（支持文件路径或内联文本）
        script_path = Path(args.script)
        if script_path.exists():
            script_text = script_path.read_text(encoding="utf-8").strip()
            print(f"  [script] 从文件读取文案: {args.script}")
        else:
            script_text = args.script.strip()
            print(f"  [script] 使用内联文案 ({len(script_text)}字)")
        
        # 按空行分段
        paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
        # 如果没有空行分段，按换行分段
        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in script_text.split("\n") if p.strip()]
        
        # 构建script_data（与script_writer输出格式一致）
        sections = []
        for i, para in enumerate(paragraphs, 1):
            sections.append({
                "section_id": i,
                "content": para,
                "talking_point": f"段落{i}"
            })
        
        # 自动推断topic（取第一段前20字）
        if not args.topic:
            auto_topic = paragraphs[0][:20] if paragraphs else "用户自定义文案"
            args.topic = auto_topic
            # 也写入topic_selected.json
            topic_file = OUTPUT_DIR / "topic_selected.json"
            topic_data = {
                "selected_topic": auto_topic,
                "topic": auto_topic,
                "angle": "用户自定义文案",
                "hook": paragraphs[0][:30] if paragraphs else "",
                "key_points": [],
                "target_audience": "",
                "sources": [],
                "score": {"total": 0, "max": 60}
            }
            topic_file.write_text(json.dumps(topic_data, ensure_ascii=False, indent=2))
        
        script_data = {
            "topic": args.topic,
            "mood": "自然",
            "voiceover_sections": sections,
            "total_chars": sum(len(s["content"]) for s in sections)
        }
        script_file.write_text(json.dumps(script_data, ensure_ascii=False, indent=2))
        print(f"  [script] 已写入 {len(sections)} 段文案 ({script_data['total_chars']}字)")
        print(f"  [script] 跳过步骤1-3 (topic_scout/topic_selector/script_writer)")
    
    # 定义pipeline步骤
    # 执行顺序：串行(1-3) → 并行(4+5+8) → 并行(6+7+9) → 串行(10-12)
    # 依赖关系：
    #   4(lyrics)依赖3(script)
    #   5(voice)依赖3(script)
    #   8(design)依赖3(script) ← 原来在步骤8，提前到这里
    #   6(transcriber)依赖5(voice)
    #   7(bgm)依赖4(lyrics)
    #   9(storyboard)依赖8(design)
    #   10(hf_builder)依赖6+7+9
    #   11(renderer)依赖10
    #   12(mixer)依赖5+7+11
    
    import threading
    
    def should_run(skill_name):
        """检查skill是否应该运行（考虑skip flags和step range）"""
        step_map = {
            "topic_scout": 1, "topic_selector": 2, "script_writer": 3,
            "lyrics_writer": 4, "voice_gen": 5, "transcriber": 6,
            "bgm_generator": 7, "design_system": 8, "storyboard": 9,
            "hf_builder": 10, "video_renderer": 11, "audio_mixer": 12,
        }
        step_num = step_map.get(skill_name, 0)
        if step_num < start_step or step_num > end_step:
            return False
        if args.topic and skill_name in ("topic_scout", "topic_selector"):
            return False
        if args.script and skill_name in ("topic_scout", "topic_selector", "script_writer"):
            return False
        if args.skip_voice and skill_name == "voice_gen":
            return False
        if args.skip_bgm and skill_name in ("lyrics_writer", "bgm_generator"):
            return False
        return True
    
    def run_skill(skill_name, step_num):
        """运行单个skill（线程安全）"""
        if not should_run(skill_name):
            print(f"\n[Step {step_num}] {skill_name}: 跳过")
            return None
        # 获取优化提示
        if FEEDBACK_ENABLED:
            hints = get_optimization_hints(skill_name)
            if hints:
                print(f"  💡 历史优化提示: {hints}")
                context["_optimization_hints"] = hints
        result = run_step(skill_name, context, step_num)
        context.pop("_optimization_hints", None)
        if FEEDBACK_ENABLED and skill_name in ["script_writer", "voice_gen", "bgm_generator", "storyboard", "hf_builder"]:
            check_skill_quality_after_step(skill_name, result)
        return result
    
    def run_parallel(skills):
        """并行运行多个skill，返回所有结果
        skills: list of (skill_name, step_num)
        """
        results = {}
        threads = []
        errors = []
        
        def worker(name, num):
            try:
                ctx = run_skill(name, num)
                if ctx is not None:
                    results[name] = ctx
            except Exception as e:
                errors.append((name, e))
        
        for name, num in skills:
            t = threading.Thread(target=worker, args=(name, num), daemon=True)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        if errors:
            for name, e in errors:
                print(f"  ❌ {name} 并行执行失败: {e}")
            sys.exit(1)
        
        return results
    
    # === Phase 1: 串行 1-3 ===
    for skill in ["topic_scout", "topic_selector", "script_writer"]:
        step_num = {"topic_scout": 1, "topic_selector": 2, "script_writer": 3}[skill]
        run_skill(skill, step_num)
    
    # 验证选题质量（topic_selector完成后）
    topic = context.get("selected_topic") or context.get("topic") or ""
    if not topic or topic in ("无可用信息", "None", ""):
        print(f"\n🛑 选题失败: topic='{topic}'，Pipeline终止")
        print(f"  提示: topic_selector JSON解析失败，请检查LLM返回格式")
        sys.exit(1)
    # 确保context中有topic字段
    context["topic"] = topic
    print(f"  ✅ 选题验证通过: {topic[:50]}")
    
    # === Phase 2: 并行 4(lyrics) + 5(voice) + 8(design) ===
    print(f"\n{'='*60}")
    print(f"⚡ Phase 2: 并行执行 lyrics_writer + voice_gen + design_system")
    print(f"{'='*60}")
    run_parallel([
        ("lyrics_writer", 4),
        ("voice_gen", 5),
        ("design_system", 8),
    ])
    
    # === Phase 3: 并行 6(transcriber) + 7(bgm) + 9(storyboard) ===
    # 6依赖5(voice), 7依赖4(lyrics), 9依赖8(design)
    print(f"\n{'='*60}")
    print(f"⚡ Phase 3: 并行执行 transcriber + bgm_generator + storyboard")
    print(f"{'='*60}")
    run_parallel([
        ("transcriber", 6),
        ("bgm_generator", 7),
        ("storyboard", 9),
    ])
    
    # === Phase 4: 串行 10-12 ===
    run_skill("hf_builder", 10)
    
    # 反哺：hf_builder完成后自动诊断场景质量
    try:
        from pipeline_reviewer import analyze_all_scenes, print_report, generate_fix_instructions
        compositions_dir = str(HF_PROJECT / "hf_render_project" / "compositions")
        report = analyze_all_scenes(compositions_dir)
        if "error" not in report:
            print_report(report)
            fixes = generate_fix_instructions(report)
            critical_fixes = [f for f in fixes if f["severity"] == "critical"]
            if critical_fixes:
                print(f"\n  ⚠️ 发现{len(critical_fixes)}个严重质量问题，但不阻断pipeline")
                # 保存诊断报告到output目录
                report_path = OUTPUT_DIR / "quality_diagnosis.json"
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                print(f"  📋 诊断报告: {report_path}")
            else:
                print(f"\n  ✅ 所有场景质量达标")
            
            # === 反哺闭环：写入feedback_history.json ===
            feedback_path = OUTPUT_DIR / "feedback_history.json"
            feedback_entry = {
                "timestamp": datetime.now().isoformat(),
                "topic": context.get("topic", ""),
                "total_scenes": report.get("total_scenes", 0),
                "passed_scenes": report.get("passed_scenes", 0),
                "issues": [],
            }
            for scene in report.get("scenes", []):
                for issue in scene.get("issues", []):
                    feedback_entry["issues"].append({
                        "scene": scene.get("scene_name", ""),
                        "check": issue.get("check_name", ""),
                        "severity": issue.get("severity", ""),
                        "message": issue.get("message", ""),
                    })
            # 追加到历史文件
            history = []
            if feedback_path.exists():
                try:
                    with open(feedback_path, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"  ⚠️ 读取反馈历史失败: {e}")
                    history = []
            history.append(feedback_entry)
            # 只保留最近10次
            history = history[-10:]
            with open(feedback_path, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            print(f"  📝 反哺历史已更新: {feedback_path}")
    except Exception as e:
        print(f"  ⚠️ 质量诊断跳过: {e}")
    
    for skill in ["video_renderer", "audio_mixer"]:
        step_num = {"video_renderer": 11, "audio_mixer": 12}[skill]
        run_skill(skill, step_num)
    
    # 最终质量追溯
    if FEEDBACK_ENABLED:
        print(f"\n{'='*60}")
        print(f"📊 最终质量追溯")
        print(f"{'='*60}")
        report = trace_failure(context)
        if report["summary"]["total_issues"] > 0:
            print(f"  ⚠️ 发现 {report['summary']['total_issues']} 个问题")
            print(f"  📋 报告: {FEEDBACK_DIR / 'logs' / 'quality_reports'}")
        else:
            print(f"  ✅ 所有质量检查通过")
    
    # 保存context
    context_path = OUTPUT_DIR / "pipeline_context.json"
    with open(context_path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2, default=str)
    
    
    # 生成元数据
    try:
        from generate_metadata import generate_metadata
        metadata = generate_metadata(context)
        meta_path = OUTPUT_DIR / "metadata.json"
        print(f"  📋 元数据: {meta_path}")
        title = metadata["title"]
        tags = " ".join(metadata["hashtags"])
        print(f"  📝 标题: {title}")
        print(f"  🏷️ 标签: {tags}")
    except Exception as e:
        print(f"  ⚠️ 元数据生成失败: {e}")
    print(f"\n{'='*60}")
    print(f"✅ Pipeline完成!")
    print(f"{'='*60}")
    print(f"最终视频: {context.get('mixed_path', 'N/A')}")
    print(f"配音: {context.get('voice_path', 'N/A')}")
    bgm = context.get('bgm_path')
    if not bgm:
        print(f"⚠️ BGM: 未生成（无背景音乐）")
    else:
        print(f"BGM: {bgm}")
    print(f"Context: {context_path}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
