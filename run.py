#!/usr/bin/env python3
"""
run.py — video-factory 新入口（YAML 驱动 + Provider 抽象 + 成本追踪）

用法:
    python run.py --topic "话题"              # 完整 pipeline
    python run.py --topic "话题" --steps 10-12 # 只跑渲染步骤
    python run.py --list                       # 列出可用 pipeline
    python run.py --pipeline short_video --topic "..."  # 指定 pipeline
"""

import os
import sys
from pathlib import Path

# 清除 PYTHONPATH 防止 hermes-agent venv 覆盖 core venv
if "PYTHONPATH" in os.environ:
    del os.environ["PYTHONPATH"]
sys.path[:] = [
    p for p in sys.path
    if not any(x in p.lower() for x in ["hermes-agent", "hermes_agent"])
    or "core" in p.lower()
]

# 确保 core venv 的 site-packages 在 sys.path 中
import platform
_hermes_home = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
if platform.system() == "Windows":
    _core_site = _hermes_home / "core" / "venv" / "Lib" / "site-packages"
else:
    _core_site = _hermes_home / "core" / "venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
if _core_site.exists() and str(_core_site) not in sys.path:
    sys.path.insert(0, str(_core_site))

# 加载 .env
WORKSPACE = Path(__file__).parent


def load_env():
    env_files = [
        WORKSPACE / ".env",
        WORKSPACE / "video-factory-clawhub" / ".env",
    ]
    for env_file in env_files:
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())


load_env()

# 路径设置
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "hf-project"))
sys.path.insert(0, str(WORKSPACE / "src"))

# 导入 pipeline_loader
from pipeline_loader import run_pipeline, list_pipelines, load_pipeline

# 可选：导入 cost_tracker
try:
    from cost_tracker import CostTracker
    COST_TRACKER_AVAILABLE = True
except ImportError:
    COST_TRACKER_AVAILABLE = False


def _archive_to_feishu(topic: str = "") -> bool:
    """pipeline 跑完归档到飞书「AI 输出」台账 + 输出区。失败静默降级（不影响成品）。"""
    try:
        import json
        from feishu_archive import archive_task
        output_dir = WORKSPACE / "hf-project" / "output"
        meta_path = output_dir / "publish_meta.json"

        # 高清版优先（4K step11_final_2x.mp4），缺失降级 1080p
        video_path = output_dir / "step11_final_2x.mp4"
        if not video_path.exists():
            video_path = output_dir / "step11_final.mp4"
        if not video_path.exists():
            return False

        title = topic or ""
        description = ""
        tags = []
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            title = meta.get('title', title)
            description = meta.get('description', '')
            tags = meta.get('tags', [])
        else:
            # 🔴 publish_meta 是 optional 步骤（可能被跳过），兜底从必产出文件提取元数据
            #    （定时任务跳过 publish_meta 时，视频仍应归档，不能静默丢同步）
            script_path = output_dir / "step03_script.json"
            if script_path.exists():
                script = json.loads(script_path.read_text(encoding='utf-8'))
                _t = (script.get('topic', '') or topic or '').strip()
                title = _t[:20] if len(_t) > 20 else _t
                topic = title
            # tags 从标题兜底提取（2-4 字关键词粗提取，非关键）
            if title:
                tags = [w for w in title.replace('：', ' ').replace(':', ' ').split() if 2 <= len(w) <= 8][:4]

        bgm_path = output_dir / "bgm.wav"
        lyrics_path = output_dir / "lyrics.txt"
        return archive_task({
            'topic': topic or title,
            'mode': 'video-factory',
            'title': title or topic,
            'description': description,
            'tags': tags,
            'video': str(video_path),
            'bgm': str(bgm_path) if bgm_path.exists() else None,
            'lyrics': str(lyrics_path) if lyrics_path.exists() else None,
            'status': '完成',
        })
    except Exception as e:
        print(f"  [feishu] 归档失败（不影响成品）: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="短视频工厂 — YAML驱动Pipeline v5")
    parser.add_argument("--pipeline", default="short_video", help="Pipeline 名称")
    parser.add_argument("--topic", help="视频话题")
    parser.add_argument("--script", help="直接提供文案（文件路径或内联文本）")
    parser.add_argument("--speech", help="口语转视频：直接说一段话，引擎帮你整理成脚本并做成视频")
    parser.add_argument("--skip-voice", action="store_true", help="跳过配音")
    parser.add_argument("--skip-bgm", action="store_true", help="跳过BGM")
    parser.add_argument("--steps", default="1-13", help="步骤范围")
    parser.add_argument("--vertical", action="store_true", help="竖屏模式")
    parser.add_argument("--supersample", action="store_true", help="V6: 2x 超采样渲染（渲染4K→缩放到1080p）")
    parser.add_argument("--no-feedback", action="store_true", help="禁用反馈系统")
    parser.add_argument("--no-cost", action="store_true", help="禁用成本追踪")
    parser.add_argument("--clean", action="store_true", help="清理 output/ 中间文件后运行")
    parser.add_argument("--list", action="store_true", help="列出所有 pipeline")
    args = parser.parse_args()

    if args.list:
        print("可用 Pipelines:")
        for p in list_pipelines():
            manifest = load_pipeline(p)
            print(f"  {p}: {manifest.get('description', '')}")
        return

    # 初始化 cost tracker
    cost_tracker = None
    if COST_TRACKER_AVAILABLE and not args.no_cost:
        output_dir = WORKSPACE / "hf-project" / "output"
        cost_tracker = CostTracker(
            output_dir=str(output_dir),
            budget_total_usd=2.0,
            mode="warn",
        )
        print(f"💰 成本追踪已启用 (预算: $2.00)")

    # --speech 自动切换到 speech_to_video 管道
    if args.speech:
        args.pipeline = "speech_to_video"

    # 执行 pipeline
    run_pipeline(
        pipeline_name=args.pipeline,
        topic=args.topic,
        script=args.script,
        speech=args.speech,
        steps=args.steps,
        skip_voice=args.skip_voice,
        skip_bgm=args.skip_bgm,
        vertical=args.vertical,
        supersample=args.supersample,
        no_feedback=args.no_feedback,
        cost_tracker=cost_tracker,
        clean=args.clean,
    )

    # 🔴 飞书归档：pipeline 跑完自动备份到「AI 输出」台账 + 输出区（失败静默降级，不影响成品）
    _archive_to_feishu(args.topic)

    # 打印费用摘要
    if cost_tracker:
        cost_tracker.print_summary()


if __name__ == "__main__":
    main()
