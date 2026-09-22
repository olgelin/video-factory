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
    """主入口：MiniMax Music3 生成 BGM（ACEStep 降级兜底）"""

    # 读取歌词
    lyrics_path = context.get("lyrics_path") or str(OUTPUT_DIR / "lyrics.txt")
    if not os.path.exists(lyrics_path):
        print(f"  ❌ [bgm-gen] 找不到歌词: {lyrics_path}")
        return context

    with open(lyrics_path, "r", encoding="utf-8") as f:
        lyrics_text = f.read().strip()

    # 目标时长（max_duration 上限设 300s，让模型自由发挥；实际时长由歌词结构+内容量+副歌重复决定）
    target_duration = float(context.get("target_duration", 300))

    # 读音乐风格 caption（lyrics_writer 产出，三段式；无则兜底完整歌曲）
    caption = context.get("music_caption", "")
    if not caption:
        caption_path = context.get("music_caption_path") or str(OUTPUT_DIR / "music_caption.txt")
        if os.path.exists(caption_path):
            with open(caption_path, "r", encoding="utf-8") as f:
                caption = f.read().strip()
    if not caption:
        caption = ("Global Metadata: Mandopop ballad, warm and emotional, mid tempo, clean modern production.\n\n"
                   "Vocal Details: warm male or female lead vocal, expressive delivery, soft harmonies in chorus.\n\n"
                   "Arrangement: piano intro, verses with gentle accompaniment, full band in chorus, bridge, warm resolve.")

    print(f"  [bgm-gen] 歌词: {lyrics_path}")
    print(f"  [bgm-gen] 目标时长上限: {target_duration}s（实际时长由歌词结构+内容量+副歌重复决定）")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from tool_runner import call_minimax_music3, call_acestep

    # 首选 MiniMax Music3
    engine = "minimax_music3"
    result = call_minimax_music3(
        caption=caption,
        lyrics=lyrics_text,
        output_path=str(BGM_PATH),
        duration=target_duration,
    )

    if result.get("error"):
        print(f"  ⚠️ [bgm-gen] Music3 失败，降级 ACEStep: {result['error']}")
        engine = "acestep"
        captions = context.get("bgm_captions", "electronic, tech, cinematic, 100 BPM")
        result = call_acestep(
            lyrics_path=lyrics_path,
            output_path=str(BGM_PATH),
            duration=target_duration,
            captions=captions,
        )

    if result.get("error"):
        print(f"  ❌ [bgm-gen] 失败: {result['error']}")
        return context

    # 更新 context
    context["bgm_path"] = str(BGM_PATH)
    context["bgm_duration"] = result.get("duration", 0)
    context["bgm_engine"] = engine

    print(f"  [bgm-gen] ✅ BGM生成完成: {context['bgm_duration']:.1f}s（引擎: {engine}）")
    return context


if __name__ == "__main__":
    test_context = {
        "lyrics_path": str(OUTPUT_DIR / "lyrics.txt"),
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  BGM路径: {result.get('bgm_path')}")
    print(f"  时长: {result.get('bgm_duration')}")
