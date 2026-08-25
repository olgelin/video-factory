"""
bgm_generator/impl.py — ACE-Step BGM生成 V4（工具隔离版）
通过tool_runner调用独立venv中的ACE-Step CLI
"""

import os
import json
import random
import re
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
BGM_PATH = OUTPUT_DIR / "bgm.wav"

# V41: 音乐时长按歌词长度微调（210-280秒区间，不再锁死固定值）
_MIN_DURATION = 210  # 3分30秒
_MAX_DURATION = 280  # 4分40秒


def _calc_duration_by_lyrics(lyrics_text: str) -> float:
    """根据歌词长度在 210-280 秒区间内推算时长 + 随机抖动"""
    # 去掉结构标记 [Chorus] 等 + 非中文字符，统计有效字数
    clean = re.sub(r'\[.*?\]', '', lyrics_text)
    clean = re.sub(r'[^\u4e00-\u9fff]', '', clean)
    char_count = len(clean)

    # 线性映射：200字→210s，500字→280s，中间线性插值
    base = _MIN_DURATION + (char_count - 200) / (500 - 200) * (_MAX_DURATION - _MIN_DURATION)
    base = max(_MIN_DURATION, min(_MAX_DURATION, base))

    # 随机抖动 ±8 秒（让每首歌时长有变化，不锁死）
    jitter = random.uniform(-8, 8)
    duration = base + jitter
    return round(max(_MIN_DURATION, min(_MAX_DURATION, duration)), 1)


def run(context: dict) -> dict:
    """主入口：通过subprocess调用ACE-Step"""

    # 读取歌词
    lyrics_path = context.get("lyrics_path") or str(OUTPUT_DIR / "lyrics.txt")
    if not os.path.exists(lyrics_path):
        print(f"  ❌ [bgm-gen] 找不到歌词: {lyrics_path}")
        return context

    # V41: 按歌词长度自动推算时长（210-280秒区间，不再锁死）
    with open(lyrics_path, "r", encoding="utf-8") as f:
        lyrics_text = f.read().strip()

    bgm_duration = _calc_duration_by_lyrics(lyrics_text)
    captions = context.get("bgm_captions", "electronic, tech, cinematic, 100 BPM, suspenseful to inspirational")

    print(f"  [bgm-gen] 歌词: {lyrics_path}")
    print(f"  [bgm-gen] 时长: {bgm_duration}s（按歌词长度自动推算，区间 210-280s）")

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
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  BGM路径: {result.get('bgm_path')}")
    print(f"  时长: {result.get('bgm_duration')}")
