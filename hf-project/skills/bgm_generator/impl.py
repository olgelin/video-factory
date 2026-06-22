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
import sys
from pathlib import Path

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


def generate_bgm(lyrics: str, output_path: str, bgm_duration: float = 210) -> tuple:
    """生成BGM，根据配音时长自动匹配"""
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
        
        # 默认3分30秒，独立于配音时长（16GB GPU上限360s）
        bgm_duration = min(210, 360)  # 210s = 3:30
        print(f"  [bgm-gen] 目标BGM时长: {bgm_duration:.1f}s")
        
        # 多次尝试策略
        attempts = [
            # 尝试1: 关闭tiled_decode，指定时长
            {"use_tiled_decode": False, "audio_duration": bgm_duration},
            # 尝试2: 开启tiled_decode，指定时长
            {"use_tiled_decode": True, "audio_duration": bgm_duration},
            # 尝试3: 关闭tiled_decode，不锁时长
            {"use_tiled_decode": False, "audio_duration": -1},
        ]
        
        for i, params in enumerate(attempts):
            print(f"  [bgm-gen] 尝试 {i+1}/3: tiled_decode={params['use_tiled_decode']}, duration={params['audio_duration']}")
            
            # 清理GPU缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            def do_generate(p=params):
                return handler.generate_music(
                    captions="electronic, tech, cinematic, 100 BPM, suspenseful to inspirational",
                    lyrics=lyrics,
                    vocal_language="zh",
                    audio_duration=p["audio_duration"],
                    inference_steps=8,
                    guidance_scale=1.0,  # turbo模型固定1.0
                    use_random_seed=True,
                    seed=-1,
                    task_type="text2music",
                    use_tiled_decode=p["use_tiled_decode"],
                )
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(do_generate)
                try:
                    timeout = 300 if i == 0 else 180  # 第一次5分钟，后面3分钟
                    result = future.result(timeout=timeout)
                    
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
                    
                    if audio_data is not None:
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
                        
                        print(f"  [bgm-gen] ✅ 成功: {output_path} ({duration_actual:.1f}s)")
                        return output_path, duration_actual
                    
                    print(f"  [bgm-gen] 尝试{i+1}无法提取音频数据，重试...")
                    
                except TimeoutError:
                    print(f"  [bgm-gen] 尝试{i+1}超时，重试...")
                    # 强制取消线程
                    future.cancel()
                    
        # 所有尝试都失败
        print(f"  [bgm-gen] ❌ 所有尝试都失败")
        return None, 0
        
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
    
    # BGM时长（默认3:30，不依赖配音）
    bgm_target_duration = context.get("bgm_duration", 210)
    print(f"  [bgm-gen] 目标BGM时长: {bgm_target_duration:.1f}s")
    
    # 生成BGM（无fallback，必须成功）
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        bgm_path, bgm_duration = generate_bgm(lyrics, str(BGM_PATH), bgm_target_duration)
        
        if bgm_path:
            context["bgm_path"] = bgm_path
            context["bgm_duration"] = bgm_duration
            print(f"  [bgm-gen] ✅ BGM生成完成 ({bgm_duration:.1f}s)")
        else:
            print(f"  ❌ [bgm-gen] BGM生成失败！Pipeline将无BGM继续")
            # 不使用fallback，但标记失败
            context["bgm_path"] = None
            context["bgm_duration"] = 0
                
    except Exception as e:
        print(f"  ❌ [bgm-gen] BGM生成异常: {e}")
        import traceback
        traceback.print_exc()
        context["bgm_path"] = None
        context["bgm_duration"] = 0
    
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