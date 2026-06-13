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

sys.path.insert(0, str(WORKSPACE / "src"))

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
    
    return context

def main():
    import argparse
    parser = argparse.ArgumentParser(description="短视频工厂 — 完整Pipeline")
    parser.add_argument("--topic", type=str, required=True, help="视频话题")
    parser.add_argument("--skip-bgm", action="store_true", help="跳过BGM生成")
    parser.add_argument("--skip-voice", action="store_true", help="跳过配音生成")
    parser.add_argument("--steps", type=str, default="1-12", help="执行步骤范围 (如 1-12)")
    args = parser.parse_args()
    
    # 解析步骤范围
    start_step, end_step = map(int, args.steps.split("-"))
    
    print(f"\n{'='*60}")
    print(f"🎬 短视频工厂 — 完整Pipeline")
    print(f"{'='*60}")
    print(f"话题: {args.topic}")
    print(f"步骤: {start_step}-{end_step}")
    print(f"输出: {OUTPUT_DIR}")
    print(f"{'='*60}")
    
    # 初始化context
    context = {
        "topic": args.topic,
        "output_dir": str(OUTPUT_DIR),
        "project_root": str(HF_PROJECT),
        "voice_path": str(OUTPUT_DIR / "step05_voice.wav"),
        "bgm_path": str(OUTPUT_DIR / "bgm.wav"),
        "video_path": str(OUTPUT_DIR / "step10_video.mp4"),
    }
    
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
            "key_elements": ["数据", "趋势", "影响"],
            "sources": [],
            "score": {"total": 55, "max": 60}
        }
        topic_file.write_text(json.dumps(topic_data, ensure_ascii=False, indent=2))
        print(f"  [topic] 已指定话题，跳过选题: {args.topic}")
    
    # 定义pipeline步骤
    steps = [
        (1, "topic_scout", "热点采集"),
        (2, "topic_selector", "选题"),
        (3, "script_writer", "剧本生成"),
        (4, "lyrics_writer", "歌词生成"),
        (5, "voice_gen", "配音生成"),
        (6, "transcriber", "语音识别"),
        (7, "bgm_generator", "BGM生成"),
        (8, "storyboard", "分镜设计"),
        (9, "design_system", "设计系统"),
        (10, "hf_builder", "HTML构建"),
        (11, "video_renderer", "视频渲染"),
        (12, "audio_mixer", "音频混合"),
    ]
    
    # 执行pipeline
    for step_num, skill_name, description in steps:
        if step_num < start_step or step_num > end_step:
            print(f"\n[Step {step_num}] {skill_name}: 跳过 (不在范围)")
            continue
        
        # 如果已指定 --topic，跳过选题步骤
        if args.topic and skill_name in ("topic_scout", "topic_selector"):
            print(f"\n[Step {step_num}] {skill_name}: 跳过 (--topic 指定)")
            continue
        
        # 跳过选项
        if args.skip_voice and skill_name == "voice_gen":
            print(f"\n[Step {step_num}] {skill_name}: 跳过 (--skip-voice)")
            continue
        if args.skip_bgm and skill_name in ("lyrics_writer", "bgm_generator"):
            print(f"\n[Step {step_num}] {skill_name}: 跳过 (--skip-bgm)")
            continue
        
        context = run_step(skill_name, context, step_num)
    
    # 保存context
    context_path = OUTPUT_DIR / "pipeline_context.json"
    with open(context_path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print(f"✅ Pipeline完成!")
    print(f"{'='*60}")
    print(f"最终视频: {context.get('mixed_path', 'N/A')}")
    print(f"配音: {context.get('voice_path', 'N/A')}")
    print(f"BGM: {context.get('bgm_path', 'N/A')}")
    print(f"Context: {context_path}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
