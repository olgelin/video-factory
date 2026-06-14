"""
bgm_generator/impl.py — BGM生成器
功能：根据歌词生成背景音乐

职责边界：
- 读取lyrics.txt（ACE-Step格式歌词）
- 用ACE-Step模型生成BGM
- 输出bgm.wav

输入：output/lyrics.txt（lyrics-writer的输出）
输出：output/bgm.wav（背景音乐）

依赖：
- acestep_package（本地安装）
- torch + torchaudio
"""

import os
import json
import re
import sys
from pathlib import Path
from datetime import datetime

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
LYRICS_PATH = OUTPUT_DIR / "lyrics.txt"
BGM_PATH = OUTPUT_DIR / "bgm.wav"

# ACE-Step模型路径
ACESTEP_ROOT = os.environ.get("ACESTEP_ROOT", "E:/Hermes-Agent/workspace/xiaoshan/models/acestep_package")
ACESTEP_CHECKPOINT = os.environ.get("ACESTEP_CHECKPOINT", "acestep-v15-turbo")


def load_env():
    """加载环境变量"""
    from dotenv import load_dotenv
    possible_envs = [
        os.path.join(os.environ.get("HERMES_HOME", ""), ".env"),
        "E:/Hermes-Agent/.env",
        os.path.expanduser("~/.env"),
    ]
    for env_path in possible_envs:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            return


def generate_bgm(lyrics: str, output_path: str) -> tuple:
    """生成BGM，不锁死时间，根据歌词自动生成"""
    import torch
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    
    print(f"  [bgm-gen] 初始化ACE-Step模型...")
    
    # 添加models目录到sys.path
    models_dir = "E:/Hermes-Agent/workspace/xiaoshan/models"
    if models_dir not in sys.path:
        sys.path.insert(0, models_dir)
    
    try:
        from acestep_package.handler import AceStepHandler
        
        # 初始化handler
        handler = AceStepHandler()
        
        # 初始化服务
        result = handler.initialize_service(
            project_root=ACESTEP_ROOT,
            config_path=ACESTEP_CHECKPOINT,
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
        
        ok = result[1]
        if not ok:
            print(f"  [bgm-gen] 初始化失败: {result[0][:200]}")
            return None, 0
        
        print(f"  [bgm-gen] 模型加载成功")
        
        # 生成BGM（不锁死时间，带超时）
        print(f"  [bgm-gen] 生成BGM（根据歌词自动生成时长）...")
        
        # 使用线程池实现超时控制（3分钟）
        def do_generate():
            return handler.generate_music(
                captions="electronic, tech, cinematic, 100 BPM, suspenseful to inspirational",
                lyrics=lyrics,
                vocal_language="zh",
                audio_duration=-1,  # 不锁死时间，让模型根据歌词自动生成
                inference_steps=8,
                guidance_scale=7.0,
                use_random_seed=True,
                seed=-1,
                task_type="text2music",
            )
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(do_generate)
            try:
                result = future.result(timeout=180)  # 3分钟超时
            except TimeoutError:
                print(f"  ⚠️ [bgm-gen] BGM生成超时（3分钟），取消任务")
                # 清理GPU内存
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                return None, 0
        
        # 提取音频
        audio_data = None
        sample_rate = 48000
        
        if isinstance(result, dict):
            if "audios" in result and result["audios"]:
                audios = result["audios"]
                if audios:
                    first = audios[0]
                    if isinstance(first, dict):
                        audio_data = first.get("tensor")
                        sample_rate = first.get("sample_rate", 48000)
                    elif hasattr(first, "tensor"):
                        audio_data = first.tensor
                        sample_rate = getattr(first, "sample_rate", 48000)
            elif "audio_data" in result:
                audio_data = result["audio_data"]
            elif "audio" in result:
                audio_data = result["audio"]
        
        if audio_data is None:
            print(f"  [bgm-gen] 无法提取音频数据")
            return None, 0
        
        # 转换为numpy
        import soundfile as sf
        if isinstance(audio_data, torch.Tensor):
            arr = audio_data.cpu().numpy()
            if arr.ndim == 2:
                arr = arr.T
            audio_data = arr
        
        # 保存WAV
        sf.write(output_path, audio_data, sample_rate)
        
        # 获取实际时长
        info = sf.info(output_path)
        duration_actual = info.frames / info.samplerate
        
        print(f"  [bgm-gen] Saved: {output_path} ({duration_actual:.1f}s)")
        return output_path, duration_actual
        
    except Exception as e:
        print(f"  [bgm-gen] 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None, 0


def run(context: dict) -> dict:
    """主入口：生成BGM"""
    
    print(f"  [bgm-gen] 开始生成BGM...")
    
    load_env()
    
    # 读取歌词
    lyrics_path = context.get("lyrics_path") or str(LYRICS_PATH)
    if not os.path.exists(lyrics_path):
        print(f"  ❌ [bgm-gen] 找不到歌词: {lyrics_path}")
        return context
    
    with open(lyrics_path, "r", encoding="utf-8") as f:
        lyrics = f.read()
    
    print(f"  [bgm-gen] 歌词长度: {len(lyrics)} 字符")
    
    # 生成BGM（带超时和fallback）
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        bgm_path, bgm_duration = generate_bgm(lyrics, str(BGM_PATH))
        
        if bgm_path:
            context["bgm_path"] = bgm_path
            context["bgm_duration"] = bgm_duration
            print(f"  [bgm-gen] ✅ BGM生成完成 ({bgm_duration:.1f}s)")
        else:
            print(f"  ⚠️ [bgm-gen] BGM生成失败，使用默认BGM")
            fallback_path = str(Path(__file__).parent.parent.parent.parent / "assets" / "default_bgm.mp3")
            if os.path.exists(fallback_path):
                import shutil
                shutil.copy(fallback_path, str(BGM_PATH))
                context["bgm_path"] = str(BGM_PATH)
                context["bgm_duration"] = 120.0
                print(f"  ✅ [bgm-gen] 使用默认BGM: {fallback_path}")
            else:
                print(f"  ❌ [bgm-gen] 默认BGM也不存在: {fallback_path}")
                
    except Exception as e:
        print(f"  ⚠️ [bgm-gen] BGM生成异常: {e}，使用默认BGM")
        import traceback
        traceback.print_exc()
        
        # Fallback
        fallback_path = str(Path(__file__).parent.parent.parent.parent / "assets" / "default_bgm.mp3")
        if os.path.exists(fallback_path):
            import shutil
            shutil.copy(fallback_path, str(BGM_PATH))
            context["bgm_path"] = str(BGM_PATH)
            context["bgm_duration"] = 120.0
            print(f"  ✅ [bgm-gen] 使用默认BGM: {fallback_path}")
    
    return context


if __name__ == "__main__":
    test_context = {
        "lyrics_path": str(LYRICS_PATH),
        "voice_duration": 60,
    }
    result = run(test_context)
    
    print(f"\n✅ 测试完成")
    print(f"  BGM路径: {result.get('bgm_path')}")
    print(f"  BGM时长: {result.get('bgm_duration')}")