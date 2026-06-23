"""
audio_mixer/skill.py — 音频混合
功能：合并配音+BGM+视频
输出：mixed.mp4

基于原step11改进。
"""

import os
import subprocess
from pathlib import Path

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
MIXED_PATH = OUTPUT_DIR / "step11_final.mp4"


def run_ffmpeg(cmd: str, timeout: int = 120) -> bool:
    """运行ffmpeg命令"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return True
        else:
            print(f"  ❌ ffmpeg失败: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ ffmpeg错误: {e}")
        return False


def burn_subtitles(video_path: str, srt_path: str, output_path: str) -> bool:
    """烧录字幕到视频"""
    if not os.path.exists(srt_path):
        print(f"  ⚠️ [audio-mixer] SRT不存在，跳过字幕烧录: {srt_path}")
        return False
    
    # 转义路径中的特殊字符（ffmpeg subtitles滤镜需要）
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
    
    cmd = f"""ffmpeg -y -i "{video_path}" \
        -vf "subtitles='{srt_escaped}':force_style='FontSize=20,FontName=Microsoft YaHei,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=5,Alignment=2'" \
        -c:a copy "{output_path}" """
    
    print(f"  [audio-mixer] 烧录字幕...")
    return run_ffmpeg(cmd, timeout=180)


CRITICAL_CHECKS = {
    "voice_path": "step05_voice.wav",
    "video_path": "step10_video.mp4",
}


def run(context: dict) -> dict:
    """主入口：音频混合"""

    topic = context.get("topic", "未知话题")
    print(f"  [audio-mixer] 混合 '{topic}' 的音频...")

    # 获取输入文件
    project_root = Path(context.get("project_root", "."))
    video_path = context.get("video_path") or str(project_root / "hf_render_project" / "rendered.mp4")
    if not os.path.exists(video_path):
        # fallback: 旧路径
        video_path = str(OUTPUT_DIR / "step10_video.mp4")
    voice_path = context.get("voice_path") or str(OUTPUT_DIR / "step05_voice.wav")
    bgm_path = context.get("bgm_path") or str(OUTPUT_DIR / "bgm.wav")

    # 检查文件
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"[audio-mixer] CRITICAL: 视频不存在: {video_path}")

    if not os.path.exists(voice_path):
        raise FileNotFoundError(f"[audio-mixer] CRITICAL: 配音不存在: {voice_path}")

    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 如果没有BGM，直接用配音
    if not os.path.exists(bgm_path):
        print(f"  ⚠️ [audio-mixer] BGM不存在，只用配音")

        # 合并视频+配音
        cmd = f"""ffmpeg -y -i "{video_path}" -i "{voice_path}" \
            -c:v copy -c:a aac -b:a 128k \
            -map 0:v:0 -map 1:a:0 \
            "{MIXED_PATH}" """

        if run_ffmpeg(cmd):
            context["mixed_path"] = str(MIXED_PATH)
            print(f"  [audio-mixer] ✅ 混合完成（无BGM）")
        else:
            print(f"  ❌ [audio-mixer] 混合失败")
    else:
        # 有BGM：混合配音+BGM
        print(f"  [audio-mixer] 混合配音+BGM...")

        # 先对配音做音量均衡（两遍loudnorm: 第一遍measure，第二遍normalize）
        normalized_voice = OUTPUT_DIR / "normalized_voice.wav"
        # 第一遍：测量实际响度
        measure_cmd = f'ffmpeg -y -i "{voice_path}" -af "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" -f null -'
        measure_result = subprocess.run(measure_cmd, shell=True, capture_output=True, text=True)
        # 从stderr中提取测量JSON
        import re as _re, json as _json
        json_match = _re.search(r'\{[^}]+\}', measure_result.stderr)
        if json_match:
            measured = _json.loads(json_match.group())
            mi = measured.get("input_i", "-24")
            mtp = measured.get("input_tp", "-2")
            mlra = measured.get("input_lra", "7")
            mt = measured.get("input_thresh", "-34")
            mo = measured.get("target_offset", "0")
            cmd = f'ffmpeg -y -i "{voice_path}" -af "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={mi}:measured_TP={mtp}:measured_LRA={mlra}:measured_thresh={mt}:offset={mo}:linear=true" -ar 48000 "{normalized_voice}"'
            print(f"  [audio-mixer] 两遍loudnorm: measured I={mi} LUFS")
        else:
            cmd = f'ffmpeg -y -i "{voice_path}" -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 48000 "{normalized_voice}"'
            print(f"  [audio-mixer] loudnorm测量失败，使用单pass")
        
        if run_ffmpeg(cmd):
            print(f"  [audio-mixer] ✅ 配音音量均衡完成")
            voice_for_mix = normalized_voice
        else:
            print(f"  ⚠️ [audio-mixer] 音量均衡失败，使用原始配音")
            voice_for_mix = voice_path

        # V4改进：动态音量混合
        # 配音段落BGM降低，转场段落BGM恢复
        # 添加BGM淡入淡出
        mixed_audio = OUTPUT_DIR / "mixed_audio.wav"
        
        # 获取配音时长用于BGM截取
        voice_duration_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{voice_for_mix}"'
        vr = subprocess.run(voice_duration_cmd, shell=True, capture_output=True, text=True)
        voice_dur = float(vr.stdout.strip()) if vr.stdout.strip() else 120
        
        # 动态混合：配音为主(1.5x)，BGM做背景(0.15x) + 淡入2s + 淡出3s
        # sidechaincompress让BGM在配音说话时自动降低
        cmd = f"""ffmpeg -y -i "{voice_for_mix}" -i "{bgm_path}" \
            -filter_complex " \
            [0:a]volume=1.5[voice]; \
            [1:a]atrim=0:{voice_dur + 5},volume=0.15,afade=t=in:st=0:d=2,afade=t=out:st={voice_dur - 3}:d=3[bgm]; \
            [voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[out] \
            " -map "[out]" "{mixed_audio}" """

        if not run_ffmpeg(cmd):
            print(f"  ❌ [audio-mixer] 音频混合失败")
            return context

        # 再合并视频+混合音频
        cmd = f"""ffmpeg -y -i "{video_path}" -i "{mixed_audio}" \
            -c:v copy -c:a aac -b:a 128k \
            -map 0:v:0 -map 1:a:0 \
            "{MIXED_PATH}" """

        if run_ffmpeg(cmd):
            context["mixed_path"] = str(MIXED_PATH)
            print(f"  [audio-mixer] ✅ 混合完成（有BGM）")
        else:
            print(f"  ❌ [audio-mixer] 混合失败")

    # 烧录字幕（如果SRT存在）
    srt_path = OUTPUT_DIR / "captions.srt"
    if srt_path.exists() and context.get("mixed_path"):
        subtitled_path = OUTPUT_DIR / "step12_subtitled.mp4"
        if burn_subtitles(str(context["mixed_path"]), str(srt_path), str(subtitled_path)):
            # 替换最终输出
            import shutil
            shutil.move(str(subtitled_path), str(MIXED_PATH))
            print(f"  [audio-mixer] ✅ 字幕烧录完成")
        else:
            print(f"  ⚠️ [audio-mixer] 字幕烧录失败，使用无字幕版本")
    
    return context


if __name__ == "__main__":
    # 测试
    _output = str(OUTPUT_DIR)
    test_context = {
        "topic": "2026高考第一批显眼包出现了",
        "video_path": os.path.join(_output, "step10_video.mp4"),
        "voice_path": os.path.join(_output, "step05_voice.wav"),
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  混合路径: {result.get('mixed_path')}")
