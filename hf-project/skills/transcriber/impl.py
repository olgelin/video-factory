"""
transcriber/skill.py — faster-whisper时间戳生成
功能：用faster-whisper转录音频，生成精确逐词时间戳
输出：whisperx_transcript.json + captions.srt

v30: 从WhisperX改为faster-whisper（纯CPU，无torchcodec依赖）
"""

import os
import json
from pathlib import Path

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
TRANSCRIPT_PATH = OUTPUT_DIR / "whisperx_transcript.json"
CAPTIONS_PATH = OUTPUT_DIR / "captions.srt"


def run_faster_whisper(audio_path: str) -> dict:
    """用FunASR转录音频（替代faster_whisper，解决numpy兼容问题）"""
    try:
        from funasr import AutoModel
    except ImportError:
        print(f"  ❌ [transcriber] FunASR不可用，尝试fallback方案")
        return None

    print(f"  [transcriber] Loading FunASR (paraformer-zh)...")
    try:
        model = AutoModel(model='paraformer-zh', model_revision='v2.0.4', disable_update=True)
    except Exception as e:
        print(f"  ❌ [transcriber] FunASR模型加载失败: {e}")
        return None

    print(f"  [transcriber] Transcribing: {audio_path}")
    try:
        result = model.generate(input=audio_path, batch_size_s=300)
    except Exception as e:
        print(f"  ❌ [transcriber] FunASR转录失败: {e}")
        return None

    if not result:
        print(f"  ❌ [transcriber] FunASR返回空结果")
        return None

    # 转换FunASR输出为标准格式
    segments = []
    for item in result:
        text = item.get('text', '')
        # FunASR返回的timestamp是字符级时间戳
        timestamp = item.get('timestamp', [])
        
        if timestamp and len(timestamp) >= 2:
            # 有时间戳：用第一个和最后一个
            start = timestamp[0][0] / 1000.0  # 毫秒转秒
            end = timestamp[-1][1] / 1000.0
        else:
            # 无时间戳：估算
            start = 0
            end = len(text) * 0.15  # 粗略估算：每字0.15秒
        
        segments.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "text": text.strip(),
            "words": [],
        })

    # 计算总时长
    total_duration = segments[-1]["end"] if segments else 0

    transcript = {
        "segments": segments,
        "language": "zh",
        "duration": total_duration,
    }

    print(f"  [transcriber] ✅ 转录完成: {len(segments)} segments, {total_duration:.1f}s")
    return transcript


def generate_srt_from_voice_durations(voice_scene_durs: list, output_path: str, max_chars: int = 18):
    """用voice_scene_durations生成近似SRT（当ASR不可用时的fallback）"""
    if not voice_scene_durs:
        print(f"  ⚠️ [transcriber] 无配音时长数据，无法生成SRT")
        return

    entries = []
    cumulative = 0.0

    for i, vsd in enumerate(voice_scene_durs):
        text = vsd.get("text", "")
        duration = vsd.get("duration", 5.0)
        start = cumulative
        end = cumulative + duration
        cumulative = end

        # 将长文本拆分为多行字幕
        if len(text) <= max_chars:
            entries.append({"start": start, "end": end, "text": text})
        else:
            # 按标点拆分
            chunks = []
            remaining = text
            while remaining:
                if len(remaining) <= max_chars:
                    chunks.append(remaining)
                    break
                # 找最近的标点断行
                cut = max_chars
                for punct in "，。、；！？,.;!? ":
                    idx = remaining[:max_chars].rfind(punct)
                    if idx > max_chars // 2:
                        cut = idx + 1
                        break
                chunks.append(remaining[:cut].strip())
                remaining = remaining[cut:].strip()
            
            # 按字数比例分配时间
            total_chars = sum(len(c) for c in chunks)
            current_start = start
            for chunk in chunks:
                chunk_dur = duration * len(chunk) / total_chars if total_chars > 0 else duration / len(chunks)
                current_end = min(current_start + chunk_dur, end)
                if current_end > current_start:  # 确保时间戳有效
                    entries.append({"start": current_start, "end": current_end, "text": chunk})
                current_start = current_end

    # 生成SRT
    srt_content = ""
    for i, entry in enumerate(entries):
        srt_content += f"{i+1}\n"
        srt_content += f"{_format_srt_time(entry['start'])} --> {_format_srt_time(entry['end'])}\n"
        srt_content += f"{entry['text']}\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"  [transcriber] 近似SRT已保存: {output_path} ({len(entries)} 条)")


def _format_srt_time(seconds: float) -> str:
    """格式化SRT时间戳"""
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def generate_srt(transcript: dict, output_path: str, max_chars: int = 18, max_duration: float = 4.0):
    """生成SRT字幕文件
    
    关键改进：
    1. 长文本拆分为每行最多max_chars字
    2. 每条字幕最多max_duration秒
    3. 确保时间线连续无缺口
    """
    segments = transcript.get("segments", [])
    
    # 第一步：拆分长segment为短条目
    entries = []
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "").strip()
        if not text:
            continue
        
        dur = end - start
        if dur <= 0:
            continue
        
        # 如果文本短且时长合理，直接使用
        if len(text) <= max_chars and dur <= max_duration:
            entries.append({"start": start, "end": end, "text": text})
            continue
        
        # 拆分长文本：按max_chars分段
        chunks = []
        while text:
            if len(text) <= max_chars:
                chunks.append(text)
                break
            # 找最近的标点或空格断行
            cut = max_chars
            for punct in "，。、；！？,.;!? ":
                idx = text[:max_chars].rfind(punct)
                if idx > max_chars // 2:
                    cut = idx + 1
                    break
            chunks.append(text[:cut].strip())
            text = text[cut:].strip()
        
        if not chunks:
            continue
        
        # 按字数比例分配时间
        total_chars = sum(len(c) for c in chunks)
        current_start = start
        for chunk in chunks:
            chunk_dur = dur * len(chunk) / total_chars if total_chars > 0 else dur / len(chunks)
            chunk_dur = max(chunk_dur, 0.5)  # 最少0.5秒
            current_end = min(current_start + chunk_dur, end)
            entries.append({"start": current_start, "end": current_end, "text": chunk})
            current_start = current_end
    
    if not entries:
        print(f"  ⚠️ [transcriber] 无有效字幕条目")
        return
    
    # 第二步：修复时间线（填补缺口，消除重叠）
    entries.sort(key=lambda e: e["start"])
    for i in range(len(entries)):
        # 与前一条对齐（填补缺口）
        if i > 0:
            gap = entries[i]["start"] - entries[i-1]["end"]
            if 0 < gap < 2.0:
                # 小缺口：延伸前一条的结束时间
                entries[i-1]["end"] = entries[i]["start"]
            elif gap < 0:
                # 重叠：截断前一条
                entries[i-1]["end"] = entries[i]["start"]
        
        # 限制单条时长
        if entries[i]["end"] - entries[i]["start"] > max_duration:
            entries[i]["end"] = entries[i]["start"] + max_duration
    
    # 第三步：生成SRT
    srt_content = ""
    for i, entry in enumerate(entries):
        srt_content += f"{i+1}\n"
        srt_content += f"{_format_srt_time(entry['start'])} --> {_format_srt_time(entry['end'])}\n"
        srt_content += f"{entry['text']}\n\n"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
    
    print(f"  [transcriber] SRT已保存: {output_path} ({len(entries)} 条)")


def run(context: dict) -> dict:
    """主入口：转录音频"""

    voice_path = context.get("voice_path") or str(OUTPUT_DIR / "step05_voice.wav")
    if not os.path.exists(voice_path):
        print(f"  ❌ [transcriber] 找不到音频: {voice_path}")
        return context

    print(f"  [transcriber] 转录: {voice_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    transcript = run_faster_whisper(voice_path)

    if not transcript or not transcript.get("segments"):
        # FunASR失败，用voice_scene_durations生成近似SRT
        print(f"  ⚠️ [transcriber] ASR转录失败，使用voice_scene_durations生成近似SRT")
        vsd_path = OUTPUT_DIR / "voice_scene_durations.json"
        if vsd_path.exists():
            with open(vsd_path, "r", encoding="utf-8") as f:
                voice_scene_durs = json.load(f)
            generate_srt_from_voice_durations(voice_scene_durs, str(CAPTIONS_PATH))
            context["captions_path"] = str(CAPTIONS_PATH)
            print(f"  [transcriber] ✅ 近似SRT生成完成")
        else:
            print(f"  ❌ [transcriber] voice_scene_durations.json也不存在，无法生成SRT")
        return context

    with open(TRANSCRIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    print(f"  [transcriber] Transcript已保存: {TRANSCRIPT_PATH}")

    generate_srt(transcript, str(CAPTIONS_PATH))

    segments = transcript.get("segments", [])
    total_words = sum(len(seg.get("text", "")) for seg in segments)
    duration = segments[-1].get("end", 0) if segments else 0

    print(f"  [transcriber] ✅ 转录完成: {len(segments)} 个片段, {total_words} 字, {duration:.1f}s")

    context["transcript_path"] = str(TRANSCRIPT_PATH)
    context["captions_path"] = str(CAPTIONS_PATH)
    context["transcript_data"] = transcript

    return context


if __name__ == "__main__":
    _output = str(OUTPUT_DIR)
    test_context = {
        "voice_path": os.path.join(_output, "step05_voice.wav"),
    }
    result = run(test_context)
