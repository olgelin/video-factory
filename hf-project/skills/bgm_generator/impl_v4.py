"""
bgm_generator/impl.py — ACE-Step BGM生成 V4（工具隔离版）
通过tool_runner调用独立venv中的ACE-Step CLI
"""

import os
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
BGM_PATH = OUTPUT_DIR / "bgm.wav"


def run(context: dict) -> dict:
    """主入口：通过subprocess调用ACE-Step"""

    # 读取歌词
    lyrics_path = context.get("lyrics_path") or str(OUTPUT_DIR / "lyrics.txt")
    if not os.path.exists(lyrics_path):
        print(f"  ❌ [bgm-gen] 找不到歌词: {lyrics_path}")
        return context

    # 参数
    bgm_duration = context.get("bgm_duration", 120)
    captions = context.get("bgm_captions", "electronic, tech, cinematic, 100 BPM, suspenseful to inspirational")

    print(f"  [bgm-gen] 歌词: {lyrics_path}")
    print(f"  [bgm-gen] 参数: duration={bgm_duration}s")

    # 输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 通过tool_runner调用ACE-Step CLI
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from tool_runner import call_acestep

    result = call_acestep(
        lyrics_path=lyrics_path,
        output_path=str(BGM_PATH),
        duration=bgm_duration,
        captions=captions,
    )

    if result.get("error"):
        print(f"  ❌ [bgm-gen] 失败: {result['error']}")
        return context

    # 更新context
    context["bgm_path"] = str(BGM_PATH)
    context["bgm_duration"] = result.get("duration", 0)

    print(f"  [bgm-gen] ✅ BGM生成完成: {context['bgm_duration']:.1f}s")
    return context


if __name__ == "__main__":
    test_context = {
        "lyrics_path": str(OUTPUT_DIR / "lyrics.txt"),
        "bgm_duration": 120,
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  BGM路径: {result.get('bgm_path')}")
    print(f"  时长: {result.get('bgm_duration')}")
