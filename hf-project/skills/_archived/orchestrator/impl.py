"""
orchestrator/skill.py — 编排层
功能：调度所有skill，生成完整视频
输入：topic → 输出：final.mp4

使用方法：
  python skills/orchestrator/impl.py --topic "话题"
"""

import os
import sys
import json
import argparse
import importlib.util
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

# Skill注册表
SKILLS = {
    "script_writer": {
        "name": "口播脚本",
        "module": "skills/script_writer/impl.py",
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
    "storyboard": {
        "name": "分镜设计",
        "module": "skills/storyboard/impl.py",
        "depends": ["script_writer", "design_system"],
    },
    "visual_author": {
        "name": "HTML创作",
        "module": "skills/visual_author/impl.py",
        "depends": ["storyboard", "design_system"],
    },
    "video_renderer": {
        "name": "视频渲染",
        "module": "skills/video_renderer/impl.py",
        "depends": ["visual_author"],
    },
    "quality_gate": {
        "name": "质检",
        "module": "skills/quality_gate/impl.py",
        "depends": ["video_renderer"],
    },
    "audio_mixer": {
        "name": "音频混合",
        "module": "skills/audio_mixer/impl.py",
        "depends": ["video_renderer", "voice_gen"],
    },
    "packager": {
        "name": "封装导出",
        "module": "skills/packager/impl.py",
        "depends": ["audio_mixer", "quality_gate"],
    },
    "deliverer": {
        "name": "交付",
        "module": "skills/deliverer/impl.py",
        "depends": ["packager"],
    },
}

# 执行顺序
EXECUTION_ORDER = [
    "script_writer",
    "design_system",
    "voice_gen",
    "transcriber",
    "storyboard",
    "visual_author",
    "video_renderer",
    "quality_gate",
    "audio_mixer",
    "packager",
    "deliverer",
]


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
        skills_to_run = EXECUTION_ORDER

    if skip_skills:
        skills_to_run = [s for s in skills_to_run if s not in skip_skills]

    print(f"  执行顺序: {' → '.join(skills_to_run)}")
    print(f"  跳过: {skip_skills or '无'}")
    print()

    # 逐个执行
    start_time = datetime.now()
    CRITICAL_SKILLS = {"script_writer", "voice_gen", "storyboard", "visual_author", "video_renderer"}

    for skill_name in skills_to_run:
        try:
            context = run_skill(skill_name, context)

            # 关键步骤失败检测
            if skill_name == "script_writer" and not context.get("script_path"):
                print(f"\n❌ 关键步骤失败: script_writer 未产出脚本，终止pipeline")
                return context
            if skill_name == "voice_gen" and not (context.get("voice_path") or context.get("step05_voice_path")):
                print(f"\n❌ 关键步骤失败: voice_gen 未产出配音，终止pipeline")
                return context
            if skill_name == "storyboard" and not context.get("storyboard_path"):
                print(f"\n❌ 关键步骤失败: storyboard 未产出分镜，终止pipeline")
                return context
            if skill_name == "visual_author" and not (context.get("html_path") or context.get("composition_html") or context.get("index_html_path")):
                print(f"\n❌ 关键步骤失败: visual_author 未产出HTML，终止pipeline")
                return context
            if skill_name == "video_renderer" and not (context.get("video_path") or context.get("step10_video")):
                print(f"\n❌ 关键步骤失败: video_renderer 未产出视频，终止pipeline")
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
  QA通过: {context.get('qa_passed', 'N/A')}
""")

    return context


def main():
    parser = argparse.ArgumentParser(description="视频工厂 Pipeline")
    parser.add_argument("--topic", required=True, help="视频话题")
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
