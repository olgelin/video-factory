"""
voice_gen/impl.py — VoxCPM2配音生成 V4（工具隔离版）
通过tool_runner调用独立venv中的VoxCPM2 CLI
"""

import os
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
VOICE_PATH = OUTPUT_DIR / "step05_voice.wav"


def run(context: dict) -> dict:
    """主入口：通过subprocess调用VoxCPM2"""

    # 读取脚本
    script_path = context.get("script_path") or str(OUTPUT_DIR / "step03_script.json")
    if not os.path.exists(script_path):
        print(f"  ❌ [voice-gen] 找不到脚本: {script_path}")
        return context

    # 参考音频
    ref_wav = context.get("voice_ref") or os.environ.get(
        "VOICE_REF_WAV",
        "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/assets/reference_voice.wav"
    )

    # 参数
    speed = context.get("voice_speed", 1.2)
    cfg = context.get("voice_cfg", 2.0)
    steps = context.get("voice_steps", 10)

    print(f"  [voice-gen] 参数: speed={speed}x, cfg={cfg}, steps={steps}")
    print(f"  [voice-gen] 参考音频: {ref_wav}")

    # 输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if VOICE_PATH.exists():
        VOICE_PATH.unlink()

    # 通过tool_runner调用VoxCPM2 CLI
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from tool_runner import call_voxcpm

    result = call_voxcpm(
        input_path=script_path,
        output_path=str(VOICE_PATH),
        speed=speed,
        ref_audio=ref_wav,
        cfg=cfg,
        steps=steps,
    )

    if result.get("error"):
        print(f"  ❌ [voice-gen] 失败: {result['error']}")
        return context

    # 更新context
    context["voice_path"] = str(VOICE_PATH)
    context["voice_duration"] = result.get("duration", 0)

    # 场景时长
    scene_durations = result.get("scene_durations", [])
    if scene_durations:
        context["voice_scene_durations"] = [
            {"text": f"scene{i}", "duration": d} for i, d in enumerate(scene_durations)
        ]
        # 保存到文件
        vsd_path = OUTPUT_DIR / "voice_scene_durations.json"
        with open(vsd_path, "w", encoding="utf-8") as f:
            json.dump(context["voice_scene_durations"], f, ensure_ascii=False, indent=2)

    print(f"  [voice-gen] ✅ 配音生成完成: {context['voice_duration']:.1f}s")
    return context


if __name__ == "__main__":
    _output = str(OUTPUT_DIR)
    test_context = {
        "script_path": os.path.join(_output, "step03_script.json"),
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  配音路径: {result.get('voice_path')}")
    print(f"  时长: {result.get('voice_duration')}")
