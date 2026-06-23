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

# === 环境隔离：防止hermes-agent/venv的torch/numpy污染 ===
if 'PYTHONPATH' in os.environ:
    del os.environ['PYTHONPATH']
sys.path[:] = [p for p in sys.path if not any(x in p.lower() for x in ['hermes-agent', 'hermes_agent']) or 'core' in p.lower()]
sys.meta_path = [f for f in sys.meta_path if 'hermes' not in type(f).__module__.lower() and 'hermes' not in type(f).__name__.lower()]

# Windows DLL加载优化：减少WinError 6714
if sys.platform == 'win32':
    os.environ['CUDA_MODULE_LOADING'] = 'LAZY'  # 延迟加载CUDA模块
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'  # 减少内存碎片
    # 添加DLL搜索路径
    torch_lib = Path(os.environ.get('CONDA_PREFIX', '')) / 'Lib' / 'site-packages' / 'torch' / 'lib'
    if not torch_lib.exists():
        # 尝试从sys.path找torch
        for p in sys.path:
            candidate = Path(p) / 'torch' / 'lib'
            if candidate.exists():
                torch_lib = candidate
                break
    if torch_lib.exists():
        try:
            os.add_dll_directory(str(torch_lib))
        except (AttributeError, OSError):
            pass

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
LYRICS_PATH = OUTPUT_DIR / "lyrics.txt"
BGM_PATH = OUTPUT_DIR / "bgm.wav"

# ACE-Step模型路径
ACESTEP_ROOT = os.environ.get("ACESTEP_ROOT", "E:/Hermes-Agent/workspace/xiaoshan/models/acestep_package")
ACESTEP_CHECKPOINT = os.environ.get("ACESTEP_CHECKPOINT", "acestep-v15-turbo")


def generate_bgm(lyrics: str, output_path: str, bgm_duration: float = 210) -> tuple:
    """生成BGM，根据配音时长自动匹配"""
    import torch
    
    print(f"  [bgm-gen] 初始化ACE-Step模型...")
    
    # 添加models目录到sys.path
    # 不添加ACESTEP_ROOT到sys.path，使用已安装的acestep模块
    
    try:
        # 尝试直接导入handler，避免sys.path问题
        import time as _time
        for _retry in range(5):
            try:
                from acestep_package.handler import AceStepHandler
                break
            except (OSError, ImportError) as _e:
                if _retry < 4:
                    print(f"  [bgm-gen] import重试 {_retry+1}/5: {_e}")
                    _time.sleep(2)  # 增加等待时间
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                else:
                    raise
        
        # 初始化handler（带重试）
        for init_retry in range(3):
            try:
                handler = AceStepHandler()
                break
            except OSError as oe:
                if init_retry < 2:
                    print(f"  [bgm-gen] handler初始化OSError重试 {init_retry+1}/3: {oe}")
                    _time.sleep(3)
                else:
                    raise
        
        # 初始化服务（带重试）
        for svc_retry in range(3):
            try:
                result = handler.initialize_service(
                    project_root=ACESTEP_ROOT,
                    config_path=ACESTEP_CHECKPOINT,
                    device="cuda" if torch.cuda.is_available() else "cpu",
                )
                break
            except OSError as oe:
                if svc_retry < 2:
                    print(f"  [bgm-gen] initialize_service OSError重试 {svc_retry+1}/3: {oe}")
                    _time.sleep(3)
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                else:
                    raise
        
        ok = result[1]
        if not ok:
            print(f"  [bgm-gen] 初始化失败: {result[0][:200]}")
            return None, 0
        
        print(f"  [bgm-gen] 模型加载成功")
        
        # 使用传入的时长参数（不覆盖）
        print(f"  [bgm-gen] 目标BGM时长: {bgm_duration:.1f}s")
        
        # 多次尝试策略（120s适配16GB GPU）
        attempts = [
            {"use_tiled_decode": False, "audio_duration": bgm_duration},
            {"use_tiled_decode": True, "audio_duration": bgm_duration},
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
            
            try:
                # 带重试的generate_music调用
                for gen_retry in range(3):
                    try:
                        result = do_generate()
                        break
                    except OSError as oe:
                        if gen_retry < 2:
                            print(f"  [bgm-gen] generate_music OSError重试 {gen_retry+1}/3: {oe}")
                            import time
                            time.sleep(3)
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()
                        else:
                            raise
                
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
                
            except Exception as e:
                print(f"  [bgm-gen] 尝试{i+1}失败: {e}")
                    
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
    
    # Pre-check: verify ACE-Step model directory exists
    model_dir = Path(ACESTEP_ROOT) / "checkpoints" / ACESTEP_CHECKPOINT
    if not model_dir.exists():
        # Also check if safetensors exists at checkpoint root
        safetensors_path = Path(ACESTEP_ROOT) / "checkpoints" / "model.safetensors"
        if not safetensors_path.exists():
            print(f"  ❌ [bgm-gen] ACE-Step模型未找到！")
            print(f"     期望路径: {model_dir}")
            print(f"     备选路径: {safetensors_path}")
            print(f"     ACESTEP_ROOT={ACESTEP_ROOT}")
            print(f"     请下载模型或设置 ACESTEP_ROOT 环境变量")
            context["bgm_path"] = None
            context["bgm_duration"] = 0
            return context
        else:
            print(f"  [bgm-gen] 模型文件: {safetensors_path}")
    else:
        print(f"  [bgm-gen] 模型目录: {model_dir}")
    
    # 读取歌词
    lyrics_path = context.get("lyrics_path") or str(LYRICS_PATH)
    if not os.path.exists(lyrics_path):
        print(f"  ❌ [bgm-gen] 找不到歌词: {lyrics_path}")
        return context
    
    with open(lyrics_path, "r", encoding="utf-8") as f:
        lyrics = f.read()
    
    print(f"  [bgm-gen] 歌词长度: {len(lyrics)} 字符")
    
    # BGM时长（默认120s，16GB GPU上限；210s需要>20GB VRAM）
    bgm_target_duration = min(context.get("bgm_duration", 120), 120)
    print(f"  [bgm-gen] 目标BGM时长: {bgm_target_duration:.1f}s")
    
    # 生成BGM（带重试，最多3次）
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 清理GPU缓存，释放VoxCPM2占用的VRAM
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            free_gb = torch.cuda.mem_get_info()[0] / 1024**3
            print(f"  [bgm-gen] GPU空闲: {free_gb:.1f}GB")
    except Exception:
        pass
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"  [bgm-gen] 重试 {attempt+1}/{max_retries}...")
                import time
                time.sleep(5)  # 等待5秒让系统恢复
            
            bgm_path, bgm_duration = generate_bgm(lyrics, str(BGM_PATH), bgm_target_duration)
            
            if bgm_path:
                context["bgm_path"] = bgm_path
                context["bgm_duration"] = bgm_duration
                print(f"  [bgm-gen] ✅ BGM生成完成 ({bgm_duration:.1f}s)")
                break
            elif attempt < max_retries - 1:
                print(f"  ⚠️ [bgm-gen] 尝试{attempt+1}失败，重试中...")
                continue
            else:
                print(f"  ❌ [bgm-gen] BGM生成失败！Pipeline将无BGM继续")
                context["bgm_path"] = None
                context["bgm_duration"] = 0
                    
        except Exception as e:
            print(f"  ❌ [bgm-gen] BGM生成异常: {e}")
            import traceback
            traceback.print_exc()
            if attempt == max_retries - 1:
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