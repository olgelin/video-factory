#!/usr/bin/env python3
"""
短视频工厂 — 主入口脚本
完整流程：选题 → 口播 → 配音 → BGM → 分镜 → 设计 → 渲染 → 合成 → 检查 → 优化
"""

import sys
import argparse
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from engine import run_full_pipeline


def main():
    parser = argparse.ArgumentParser(description="短视频工厂 — 自动化视频制作")
    parser.add_argument("--topic", type=str, required=True, help="视频话题")
    parser.add_argument("--output", type=str, default=None, help="输出目录")
    parser.add_argument("--no-voice", action="store_true", help="跳过配音生成")
    parser.add_argument("--no-bgm", action="store_true", help="跳过BGM选择")
    parser.add_argument("--no-visual-check", action="store_true", help="跳过视觉检查")
    
    args = parser.parse_args()
    
    # 设置输出目录
    if args.output:
        output_dir = Path(args.output)
    else:
        safe_name = args.topic[:10].replace(" ", "_").replace("/", "_")
        output_dir = Path("output") / safe_name
    
    print(f"\n{'='*60}")
    print(f"🎬 短视频工厂 — 开始制作")
    print(f"{'='*60}")
    print(f"话题: {args.topic}")
    print(f"输出: {output_dir}")
    print(f"{'='*60}\n")
    
    # TODO: 完整流程
    # 1. 选题/热点搜索 ✅ 已通过参数传入
    # 2. 口播文案生成 ✅ 已在engine.py中实现
    # 3. 配音生成 ❌ 待实现
    # 4. BGM选择 ❌ 待实现
    # 5. 分镜数据提取 ✅ 已在engine.py中实现
    # 6. LLM创意设计 ✅ 已在engine.py中实现
    # 7. 渲染 ✅ 已在engine.py中实现
    # 8. 合成 ❌ 待实现
    # 9. 视觉检查 ✅ 已在engine.py中实现
    # 10. 迭代优化 ✅ 已在engine.py中实现
    
    # 当前只执行已实现的步骤
    result = run_full_pipeline(args.topic, output_dir)
    
    print(f"\n{'='*60}")
    print(f"✅ 视频制作完成")
    print(f"{'='*60}")
    print(f"视频: {result.get('video', 'N/A')}")
    print(f"帧数: {len(result.get('frames', []))}")
    print(f"布局: {result.get('layout_types', [])}")
    print(f"背景: {result.get('bg_types', [])}")
    print(f"{'='*60}\n")
    
    # TODO: 后续步骤
    # if not args.no_voice:
    #     generate_voice(result['storyboard'], output_dir)
    # if not args.no_bgm:
    #     select_bgm(args.topic, output_dir)
    # compose_video(result['video'], voice_files, bgm_file, output_dir)
    # if not args.no_visual_check:
    #     visual_check(output_dir)


if __name__ == "__main__":
    main()
