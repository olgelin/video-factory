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

    # V5.8: 数字→中文转换，避免TTS把21000读成"二一零零零"
    _convert_numbers_in_script(script_path)

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
        # V5.2 Fix: 删除可能存在的旧配音，防止critical check误通过
        if VOICE_PATH.exists():
            VOICE_PATH.unlink()
            print(f"  🗑️ [voice-gen] 已删除旧配音防止误用")
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


def _convert_numbers_in_script(script_path: str):
    """V5.8: 将脚本中的阿拉伯数字转为中文读法，避免TTS逐位念数字"""
    import re

    # 数字→中文映射
    DIGITS_CN = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
    UNITS = ["", "十", "百", "千"]
    BIG_UNITS = ["", "万", "亿"]

    def _num_to_cn(n: int) -> str:
        if n == 0:
            return "零"
        if n < 10:
            return DIGITS_CN[n]
        if n < 20:
            return "十" + (DIGITS_CN[n % 10] if n % 10 else "")
        if n < 100:
            return DIGITS_CN[n // 10] + "十" + (DIGITS_CN[n % 10] if n % 10 else "")
        if n < 1000:
            s = DIGITS_CN[n // 100] + "百"
            rest = n % 100
            if rest:
                if rest < 10:
                    s += "零"
                s += _num_to_cn(rest)
            return s
        if n < 10000:
            s = DIGITS_CN[n // 1000] + "千"
            rest = n % 1000
            if rest:
                if rest < 100:
                    s += "零"
                s += _num_to_cn(rest)
            return s
        if n < 100000000:
            wan = n // 10000
            rest = n % 10000
            s = _num_to_cn(wan) + "万"
            if rest:
                if rest < 1000:
                    s += "零"
                s += _num_to_cn(rest)
            return s
        return str(n)  # fallback for huge numbers

    def _replace_num(m: re.Match) -> str:
        num_str = m.group(0)
        # 年号保留（1860年、2025年）
        if re.search(r'[年]', m.string[m.end():m.end()+1] if m.end() < len(m.string) else ""):
            return num_str
        try:
            n = int(num_str)
            if n > 100000000:  # 超大数字保留原文
                return num_str
            return _num_to_cn(n)
        except ValueError:
            return num_str

    # 读取脚本
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    # 递归替换所有文本字段中的数字
    def _convert(obj):
        if isinstance(obj, str):
            # 匹配独立数字（前后非中文字符或边界）
            return re.sub(r'(?<!\d)(\d{1,8})(?!\d)', _replace_num, obj)
        elif isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_convert(v) for v in obj]
        return obj

    script = _convert(script)

    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    _output = str(OUTPUT_DIR)
    test_context = {
        "script_path": os.path.join(_output, "step03_script.json"),
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  配音路径: {result.get('voice_path')}")
    print(f"  时长: {result.get('voice_duration')}")
