"""
Video Factory Pipeline Orchestrator
功能：调度所有skill，生成完整短视频
输入：topic → 输出：final.mp4

使用方法：
  python scripts/orchestrator.py --topic "话题"
  python scripts/orchestrator.py --topic "话题" --skip voice_gen bgm_generator
  python scripts/orchestrator.py --list
"""

import os
import sys
import json
import argparse
import importlib.util
from pathlib import Path
from datetime import datetime

# 项目根目录（orchestrator.py 在 scripts/ 下，根目录是上一级）
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

# Skill注册表
SKILLS = {
    "topic_scout": {
        "name": "热点采集",
        "module": "skills/topic_scout/impl.py",
        "depends": [],
    },
    "topic_selector": {
        "name": "话题筛选",
        "module": "skills/topic_selector/impl.py",
        "depends": ["topic_scout"],
    },
    "script_writer": {
        "name": "口播脚本",
        "module": "skills/script_writer/impl.py",
        "depends": ["topic_selector"],
    },
    "lyrics_writer": {
        "name": "歌词创作",
        "module": "skills/lyrics_writer/impl.py",
        "depends": ["script_writer"],
    },
    "style_learner": {
        "name": "风格学习",
        "module": "skills/style_learner/impl.py",
        "depends": [],
    },
    "design_system": {
        "name": "设计系统",
        "module": "skills/design_system/impl.py",
        "depends": ["script_writer"],
    },
    "voice_gen": {
        "name": "配音生成",
        "module": "skills/voice_gen/impl.py",
        "depends": ["script_writer"],
    },
    "transcriber": {
        "name": "时间戳",
        "module": "skills/transcriber/impl.py",
        "depends": ["voice_gen"],
    },
    "bgm_generator": {
        "name": "BGM生成",
        "module": "skills/bgm_generator/impl.py",
        "depends": ["lyrics_writer"],
    },
    "storyboard": {
        "name": "分镜设计",
        "module": "skills/storyboard/impl.py",
        "depends": ["script_writer", "design_system"],
    },
    "asset_manager": {
        "name": "素材管理",
        "module": "skills/asset_manager/impl.py",
        "depends": ["topic_selector", "script_writer"],
    },
    "hf_builder": {
        "name": "HyperFrames构建",
        "module": "skills/hf_builder/impl.py",
        "depends": ["storyboard", "design_system"],
    },
    "video_renderer": {
        "name": "视频渲染",
        "module": "skills/video_renderer/impl.py",
        "depends": ["hf_builder"],
    },
    "audio_mixer": {
        "name": "音频混合",
        "module": "skills/audio_mixer/impl.py",
        "depends": ["video_renderer", "voice_gen", "bgm_generator"],
    },
    "packager": {
        "name": "封装导出",
        "module": "skills/packager/impl.py",
        "depends": ["audio_mixer"],
    },
}

# 执行顺序（拓扑排序）
EXECUTION_ORDER = [
    "topic_scout",
    "topic_selector",
    "script_writer",
    "lyrics_writer",
    "style_learner",       # 可并行，与script_writer无强依赖
    "design_system",
    "voice_gen",
    "transcriber",
    "bgm_generator",       # 依赖lyrics_writer
    "storyboard",
    "asset_manager",
    "hf_builder",
    "video_renderer",
    "audio_mixer",
    "packager",
]

# 关键步骤（失败则终止pipeline）
CRITICAL_SKILLS = {
    "script_writer",
    "voice_gen",
    "storyboard",
    "hf_builder",
    "video_renderer",
}


def load_skill(skill_name: str):
    """动态加载skill模块"""
    skill_info = SKILLS[skill_name]
    skill_path = PROJECT_ROOT / skill_info["module"]

    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")

    spec = importlib.util.spec_from_file_location(f"skill_{skill_name}", skill_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def run_skill(skill_name: str, context: dict, max_retries: int = 2) -> dict:
    """运行单个skill（带重试）"""
    skill_info = SKILLS[skill_name]
    print(f"\n{'='*60}")
    print(f"  [{skill_name}] {skill_info['name']}")
    print(f"{'='*60}")

    for attempt in range(1, max_retries + 1):
        try:
            module = load_skill(skill_name)
            result = module.run(context.copy())
            print(f"  [{skill_name}] ✅ 完成")
            return result

        except Exception as e:
            print(f"  [{skill_name}] ❌ 失败 (attempt {attempt}/{max_retries}): {e}")
            import traceback
            traceback.print_exc()

            if attempt < max_retries:
                print(f"  [{skill_name}] 重试...")
            else:
                print(f"  [{skill_name}] 已达最大重试次数")
                raise


def check_critical(skill_name: str, context: dict) -> bool:
    """检查关键步骤是否产出"""
    checks = {
        "script_writer": lambda c: c.get("script_path"),
        "voice_gen": lambda c: c.get("voice_path") or c.get("step05_voice_path"),
        "storyboard": lambda c: c.get("storyboard_path"),
        "hf_builder": lambda c: c.get("html_path") or c.get("composition_html") or c.get("index_html_path"),
        "video_renderer": lambda c: c.get("video_path") or c.get("step10_video"),
    }
    check_fn = checks.get(skill_name)
    if check_fn and not check_fn(context):
        print(f"\n❌ 关键步骤失败: {skill_name} 未产出预期结果，终止pipeline")
        return False
    return True


def run_pipeline(topic: str, skip_skills: list = None, only_skills: list = None):
    """运行完整pipeline"""

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    视频工厂 Pipeline                        ║
║                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                     ║
╚══════════════════════════════════════════════════════════════╝

Topic: {topic}
""")

    # 初始化context
    context = {
        "topic": topic,
        "project_root": str(PROJECT_ROOT),
        "output_dir": str(OUTPUT_DIR),
    }

    # 确定要执行的skills
    if only_skills:
        skills_to_run = [s for s in EXECUTION_ORDER if s in only_skills]
    else:
        skills_to_run = EXECUTION_ORDER[:]

    if skip_skills:
        skills_to_run = [s for s in skills_to_run if s not in skip_skills]

    print(f"  执行顺序: {' → '.join(skills_to_run)}")
    print(f"  跳过: {skip_skills or '无'}")
    print()

    # 逐个执行
    start_time = datetime.now()

    for skill_name in skills_to_run:
        try:
            context = run_skill(skill_name, context)

            # 关键步骤失败检测
            if skill_name in CRITICAL_SKILLS:
                if not check_critical(skill_name, context):
                    return context

        except Exception as e:
            print(f"\n❌ Pipeline失败于 [{skill_name}]: {e}")
            return context

    # 完成
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    Pipeline 完成                            ║
╚══════════════════════════════════════════════════════════════╝

  总耗时: {duration:.0f}s ({duration/60:.1f}分钟)
  视频路径: {context.get('video_path', 'N/A')}
""")

    return context


def main():
    parser = argparse.ArgumentParser(description="视频工厂 Pipeline")
    parser.add_argument("--topic", help="视频话题")
    parser.add_argument("--skip", nargs="+", help="跳过的skill")
    parser.add_argument("--only", nargs="+", help="只执行的skill")
    parser.add_argument("--list", action="store_true", help="列出所有skill")

    args = parser.parse_args()

    if args.list:
        print("\n可用的Skills:")
        for name, info in SKILLS.items():
            deps = ", ".join(info["depends"]) if info["depends"] else "无"
            print(f"  {name}: {info['name']} (依赖: {deps})")
        return

    if not args.topic:
        parser.error("--topic is required (unless using --list)")

    # 运行pipeline
    context = run_pipeline(
        topic=args.topic,
        skip_skills=args.skip,
        only_skills=args.only,
    )

    # 保存最终context
    final_path = OUTPUT_DIR / "final_context.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2, default=str)
    print(f"  最终context已保存: {final_path}")


if __name__ == "__main__":
    main()
