#!/usr/bin/env python3
"""
run_pipeline_v25.py - Video Factory Pipeline Runner v28
全新架构：G1固定配置 + G2动态变量池 + 刚性校验 + 最多3次重试 + 精准回滚

v29 升级（2026-05-29）：
  方案A - 音频混合重构（loudnorm+压缩，voice_vol 2.0→1.2，bgm_vol 0.15→0.4，256k AAC）
  方案B - 飞书发送升级（优先msg_type=video，降级file类型）
  方案C - 质检升级v29（音画同步<0.3s，响度LUFS，Shadow Cut v2五件套，规则库写入）
  方案D - 场景对齐验证（whisperx时间戳 vs 估算时长，偏差>20%报警）
  方案E - HyperFrames组件库v2（模板补全sprocket holes，五件套完整，GSAP统一应用）
  方案F - 自愈回路v29（L1精准回滚 + L2降级参数重跑 + G2学习）

14步流程：
  Skill 01  热点采集
  Skill 02  热点筛选
  Skill 03  主题确定
  Skill 04  文案创作
  Skill 05  歌词创作
  Skill 06  配音生成
  Skill 07  WhisperX字幕
  Skill 08  ACE歌曲生成
  Skill 09  音频适配预混
  Skill 10  HyperFrames分镜
  Skill 11  HyperFrames渲染
  Skill 12  全维度质检
  Skill 13  成片封装导出
  Skill 14  交付

用法：
  python run_pipeline_v25.py --topic "杀人犯主演电影"
  python run_pipeline_v25.py --topic "杀人犯主演电影" --steps 01-11
  python run_pipeline_v25.py --topic "杀人犯主演电影" --skip-bgm
"""

import argparse
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Pipeline root
PIPELINE_ROOT = Path(__file__).parent.parent
WORKSPACE = Path("E:/Hermes-Agent/workspace/xiaoshan/video-factory")
DEFAULT_VOICE_REF = "E:/Hermes-Agent/workspace/xiaoshan/voice-cloning/CosyVoice/custom_voices/test_ref.wav"
QUALITY_RULES_FILE = PIPELINE_ROOT / "output" / "quality_rules_library.json"

# ========== 治理层 v1: 三大治理规则 ==========
# 规则1: 路径一致性审计
# 规则2: 产出物新鲜度校验
# 规则3: 类型契约检查

class GovernanceError(Exception):
    """治理规则违反"""
    pass

def audit_paths():
    """规则1: 路径一致性审计 — 确保所有关键路径指向同一项目目录"""
    critical_paths = {
        "PIPELINE_ROOT": PIPELINE_ROOT,
        "hf_render_project": PIPELINE_ROOT / "hf_render_project",
        "compositions": PIPELINE_ROOT / "hf_render_project" / "compositions",
        "output": PIPELINE_ROOT / "output",
        "skills": PIPELINE_ROOT / "skills",
    }
    errors = []
    # 检查 hf_render_project 只在 PIPELINE_ROOT 下，不在 WORKSPACE 根目录
    workspace_hf = WORKSPACE / "hf_render_project"
    if workspace_hf.exists() and workspace_hf != critical_paths["hf_render_project"]:
        errors.append(
            f"[路径冲突] workspace根目录存在旧hf_render_project: {workspace_hf}\n"
            f"  应只在PIPELINE_ROOT下: {critical_paths['hf_render_project']}\n"
            f"  建议: 删除 {workspace_hf}"
        )
    # 检查关键目录存在性
    for name, p in critical_paths.items():
        if name in ("compositions",) and not p.exists():
            p.mkdir(parents=True, exist_ok=True)
    if errors:
        for e in errors:
            print(f"  ⚠️ [治理] {e}")
    else:
        print("  ✅ [治理] 路径一致性审计通过")

# Pipeline运行ID — 用于产出物新鲜度校验
PIPELINE_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

def check_freshness(skill_name: str, expected_files: list):
    """规则2: 产出物新鲜度校验 — 确保关键文件是本轮pipeline生成的"""
    stale = []
    for f in expected_files:
        p = Path(f) if isinstance(f, str) else f
        if not p.exists():
            continue  # 文件不存在不算stale（可能是首次生成）
        # 检查文件修改时间是否在pipeline启动之后
        mtime = datetime.fromtimestamp(p.stat().st_mtime)
        pipeline_start = datetime.strptime(PIPELINE_RUN_ID, "%Y%m%d_%H%M%S")
        if mtime < pipeline_start:
            stale.append(f"  ⚠️ [治理] {skill_name}: {p.name} 是旧文件 ({mtime:%H:%M:%S})，非本轮生成")
    if stale:
        for s in stale:
            print(s)
        return False
    return True

def coerce_llm_value(value, target_type, default=None, field_name=""):
    """规则3: 类型契约检查 — LLM输出强制类型转换"""
    if value is None:
        return default
    if isinstance(value, target_type):
        return value
    try:
        if target_type is int:
            # 处理 "200", "200.0", "200px" 等LLM常见输出
            cleaned = str(value).replace("px", "").replace("pt", "").strip()
            return int(float(cleaned))
        elif target_type is float:
            return float(str(value).replace("px", "").strip())
        elif target_type is str:
            return str(value)
        elif target_type is bool:
            return str(value).lower() in ("true", "1", "yes")
        elif target_type is list:
            if isinstance(value, str):
                return [value]
            return list(value) if value else []
    except (ValueError, TypeError):
        if field_name:
            print(f"  ⚠️ [治理] 类型转换失败: {field_name}={value!r} → {target_type.__name__}, 使用默认值 {default}")
        return default
    return value

# ========== G1: 全局固定锁死配置（只读） ==========
# 整个流程中不可修改，仅各 Skill 读取使用
G1_CONFIG = {
    # 配音配置
    "voice": {
        "model": "VoxCPM2",
        "model_path": "E:/Hermes-Agent/workspace/xiaoshan/models/models--openbmb--VoxCPM2/snapshots/bffb3df5a29440629464e5e839f4d214c8714c3d",
        "ref_audio": DEFAULT_VOICE_REF,
        "cfg": 2.0,
        "steps": 15,
        "speed": 1.15,
        "device": "auto",  # 自动GPU/CPU
    },
    # WhisperX 配置
    "whisperx": {
        "model": "tiny",
        "language": "zh",
        "device": "cuda",
        "beam_size": 5,
        "best_of": 5,
    },
    # ACE-Step BGM 配置
    "ace_step": {
        "duration": 180,  # 秒
        "model": "acestep-v15-turbo",
        "guidance_scale": 7.0,
        "device": "cuda",
    },
    # HyperFrames 渲染配置
    "hyperframes": {
        "fps": 30,
        "resolution": "landscape",  # 1920x1080
        "quality": "high",          # v25: 用 high 不用 standard
        "timeout": 1200,
    },
    # 音视频合并配置
    "audio_merge": {
        "bgm_volume": 0.5,
        "voice_volume": 1.0,
        "audio_bitrate": "192k",
        "video_bitrate": "2M",
        "sample_rate": 48000,
    },
    # 全维度质检刚性标准
    "qa_standards": {
        "min_video_duration_s": 5.0,
        "max_video_duration_s": 120.0,
        "min_audio_duration_s": 5.0,
        "max_audio_duration_s": 120.0,
        "video_codec": ["h264", "h265", "av1"],
        "audio_codec": ["aac", "mp3", "opus"],
        "min_file_size_kb": 500,         # 视频文件最小 500KB（架构级保障，防止低质量渲染通过）
        "min_width": 1280,
        "min_height": 720,
        "min_fps": 24,
        "required_visual_elements": [       # 必须包含的视觉组件数量
            "scene"
        ],
        "shadow_cut_v2_required": False,     # Shadow Cut v2 视觉风格（已禁用，用HF渲染器替代）
    },
    # Skill 重试上限
    "max_retries": 3,
}


# ========== G2: 全局动态变量池（仅新增，不修改已有内容） ==========
class G2Variables:
    """全局动态变量池，各 Skill 只能新增/读取，不能修改上游内容"""

    def __init__(self):
        self.data = {}
        self.history = []  # 记录所有写入操作（用于问题溯源）

    def write(self, key, value, skill_name="unknown"):
        """写入变量（仅当 key 不存在时写入，防止覆盖上游）"""
        if key in self.data:
            print(f"  [G2 WARN] Key '{key}' already exists, keeping original value from {self.data.get('_written_by', {}).get(key, '?')}")
            return False
        self.data[key] = value
        self.data.setdefault('_written_by', {})[key] = skill_name
        self.data.setdefault('_history', []).append({
            "time": datetime.now().isoformat(),
            "skill": skill_name,
            "key": key,
            "action": "write",
        })
        return True

    def read(self, key, default=None):
        """读取变量"""
        return self.data.get(key, default)

    def has(self, key):
        return key in self.data

    def get_all(self):
        return self.data

    def to_dict(self):
        return dict(self.data)


# ========== 质检刚性校验 ==========

def qa_check_video(video_path, standards):
    """质检：视频文件"""
    issues = []
    p = Path(video_path)

    if not p.exists():
        issues.append(f"视频文件不存在: {video_path}")
        return issues

    import subprocess
    # 文件大小
    size_kb = p.stat().st_size / 1024
    if size_kb < standards.get("min_file_size_kb", 50):
        issues.append(f"视频文件过小: {size_kb:.0f}KB < {standards['min_file_size_kb']}KB（可能是渲染失败）")

    # 读取流信息
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames",
             "-of", "json", str(video_path)],
            capture_output=True, text=True, timeout=30
        )
        info = json.loads(result.stdout)
        streams = info.get("streams", [])

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not video_stream:
            issues.append("视频流不存在（可能是渲染失败的空文件）")

        if video_stream:
            w = video_stream.get("width", 0)
            h = video_stream.get("height", 0)
            if w < standards.get("min_width", 1280) or h < standards.get("min_height", 720):
                issues.append(f"分辨率过低: {w}x{h} < {standards['min_width']}x{standards['min_height']}")

            fps_parts = str(video_stream.get("r_frame_rate", "30/1")).split("/")
            if len(fps_parts) == 2:
                fps = float(fps_parts[0]) / float(fps_parts[1])
            else:
                fps = float(fps_parts[0])
            if fps < standards.get("min_fps", 24):
                issues.append(f"帧率过低: {fps:.1f} < {standards['min_fps']}")

            codec = video_stream.get("codec_name", "")
            if codec not in standards.get("video_codec", []):
                issues.append(f"视频编码异常: {codec}")

            # 帧数验证（架构级：防止渲染不完整）
            nb_frames = video_stream.get("nb_frames")
            if nb_frames:
                # 16s @ 30fps = 480 帧
                expected_frames = video_stream.get("duration", 16) * fps
                if int(nb_frames) < expected_frames * 0.85:  # 允许 15% 误差
                    issues.append(f"帧数不足: {nb_frames} 帧（预期约 {expected_frames:.0f}，可能渲染不完整）")

        if audio_stream:
            codec = audio_stream.get("codec_name", "")
            if codec not in standards.get("audio_codec", []):
                issues.append(f"音频编码异常: {codec}")

        # 检查音频是否存在
        if not audio_stream:
            issues.append("缺少音频轨道（配音+BGM未混入）")

    except Exception as e:
        issues.append(f"FFprobe 读取失败: {e}")

    return issues


def qa_check_html(html_path, standards):
    """质检：HTML 视觉组件"""
    issues = []
    p = Path(html_path)

    if not p.exists():
        issues.append(f"HTML文件不存在: {html_path}")
        return issues

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        required = standards.get("required_visual_elements", [])
        for elem in required:
            if elem not in content:
                issues.append(f"缺少视觉组件: {elem}（Shadow Cut v2 规范要求）")

        # 检查是否有 inline style（不是外引用）
        if "data-composition-src" in content:
            issues.append("使用了 data-composition-src 外引用（应使用 inline HTML+GSAP）")

        # Impact 字体检查已禁用（HF渲染器使用系统字体）
        # if "Impact" not in content and "impact" not in content.lower():
        #     issues.append("未使用 Impact 字体（Shadow Cut v2 规范要求）")

    except Exception as e:
        issues.append(f"HTML 读取失败: {e}")

    return issues


# ========== 前置检查 ==========

def run_preflight():
    """环境检查"""
    print("=== [G1] Pre-flight Check ===")
    import subprocess, torch

    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(0)
        mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"  GPU: {gpu} ({mem:.1f} GB)")
        print(f"  PyTorch: {torch.__version__} + CUDA {torch.version.cuda}")
    else:
        print("  GPU: NOT AVAILABLE (CPU only)")

    for cmd, name in [("node --version", "Node.js"), ("npx.cmd hyperframes --version", "HyperFrames CLI"),
                       ("ffmpeg -version", "FFmpeg")]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            print(f"  {name}: {r.stdout.strip().split(chr(10))[0]}")
        except:
            print(f"  {name}: MISSING")

    print("=== [G1] Pre-flight OK ===\n")


def step_num_to_float(step_str):
    """'9a'→9.0, '9b'→9.5, '1.5'→1.5"""
    import re
    m = re.match(r'(\d+)([ab]?)(.*)', str(step_str))
    if m:
        base = float(m.group(1))
        letter = m.group(2)
        if letter == 'b':
            return base + 0.5
        return base
    try:
        return float(step_str)
    except:
        return 0.0


# ========== 加载质量规则库（越跑越聪明） ==========

def load_quality_rules():
    """从文件加载历史质检规则库"""
    if QUALITY_RULES_FILE.exists():
        try:
            with open(QUALITY_RULES_FILE, encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"past_issues": [], "past_passes": [], "optimization_rules": []}


def save_quality_rules(rules):
    """保存质量规则库"""
    QUALITY_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUALITY_RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


# ========== 核心：执行单个 Skill（带重试+校验） ==========

def run_skill(skill_name, step_num, context, g2, quality_rules):
    """
    执行单个 Skill：
    1. 传入 G1 固定配置（只读）
    2. 传入 context + g2 动态变量
    3. Skill 执行（最多3次重试）
    4. 刚性校验
    5. 通过则写入 G2，继续下一个 Skill
    6. 不通过则精准回滚
    """
    # 构建 Skill 路径
    import re
    m = re.match(r'(\d+)([ab]?)', str(step_num))
    if m:
        folder = f"step{m.group(1).zfill(2)}{m.group(2)}_{skill_name}"
    else:
        folder = f"step{int(step_num):02d}_{skill_name}"
    skill_script = PIPELINE_ROOT / "skills" / folder / "impl.py"

    if not skill_script.exists():
        print(f"  [STEP {step_num}] {skill_name}: SKIP (not found)")
        return context, g2, quality_rules, True, None

    max_retries = G1_CONFIG["max_retries"]
    last_error = None

    for attempt in range(1, max_retries + 1):
        print(f"  [STEP {step_num}] {skill_name}: Running... (尝试 {attempt}/{max_retries})")

        # 准备 Skill 入参：G1（只读配置） + context（动态变量）
        skill_context = {
            **context,
            "_skill_name": skill_name,
            "_step_num": str(step_num),
            "_attempt": attempt,
            "_g1_config": G1_CONFIG,          # 固定配置（只读）
        }

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"skill_{step_num}", skill_script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, 'run'):
                print(f"  [STEP {step_num}] {skill_name}: SKIP (no run() function)")
                return context, g2, quality_rules, True, None

            # 执行 Skill
            new_context = module.run(skill_context)

            # === 刚性校验 ===
            validation_passed, validation_issues = validate_skill_output(
                skill_name, step_num, new_context, g2
            )

            if validation_passed:
                print(f"  [STEP {step_num}] {skill_name}: OK (attempt {attempt})")
                # 合并 context：保留原 context 的 key，只更新 skill 新增/修改的 key
                for k, v in new_context.items():
                    context[k] = v
                # === 治理层: topic字段规范化 ===
                # step03可能把topic设为dict，后续step需要str
                if "topic" in context and isinstance(context["topic"], dict):
                    context["topic"] = context["topic"].get("title", str(context["topic"]))
                return context, g2, quality_rules, True, None
            else:
                last_error = f"校验失败: {'; '.join(validation_issues)}"
                print(f"  [STEP {step_num}] {skill_name}: 校验不通过 - {last_error}")

                if attempt < max_retries:
                    print(f"  → 重试（使用相同 G1 固定参数）...")
                    quality_rules.setdefault("past_issues", []).append({
                        "time": datetime.now().isoformat(),
                        "skill": skill_name,
                        "step": str(step_num),
                        "attempt": attempt,
                        "issues": validation_issues,
                    })

        except Exception as e:
            last_error = f"执行异常: {str(e)[:200]}"
            print(f"  [STEP {step_num}] {skill_name}: ERROR - {last_error}")
            traceback.print_exc()

            if attempt < max_retries:
                print(f"  → 重试...")
                quality_rules.setdefault("past_issues", []).append({
                    "time": datetime.now().isoformat(),
                    "skill": skill_name,
                    "step": str(step_num),
                    "attempt": attempt,
                    "error": str(e)[:500],
                })

    # 达到最大重试次数
    print(f"  [STEP {step_num}] {skill_name}: 失败（已重试 {max_retries} 次）")
    print(f"  最终错误: {last_error}")
    quality_rules.setdefault("past_issues", []).append({
        "time": datetime.now().isoformat(),
        "skill": skill_name,
        "step": str(step_num),
        "result": "FAILED_AFTER_RETRIES",
        "error": last_error,
    })
    return context, g2, quality_rules, False, last_error


def validate_skill_output(skill_name, step_num, context, g2):
    """
    刚性校验：各 Skill 输出是否符合标准
    返回 (passed, issues_list)
    """
    issues = []

    # Skill 06 配音：检查输出文件存在且有内容
    if skill_name == "voice":
        voice_path = context.get("voice_path") or context.get("step05_voice_path")
        if voice_path:
            p = Path(voice_path)
            if not p.exists():
                issues.append(f"配音文件不存在: {voice_path}")
            elif p.stat().st_size < 10000:  # 小于 10KB 肯定有问题
                issues.append(f"配音文件过小: {p.stat().st_size/1024:.0f}KB（生成不完整）")

    # Skill 07 WhisperX：检查时间戳
    elif skill_name == "whisperx":
        wx_path = context.get("whisperx_path")
        if wx_path:
            p = Path(wx_path)
            if not p.exists():
                issues.append(f"WhisperX 文件不存在: {wx_path}")

    # Skill 07 BGM：检查文件大小（180s BGM 应该 > 1MB）
    elif skill_name == "bgm":
        bgm_path = context.get("bgm_path") or context.get("step07_bgm_path")
        if bgm_path:
            p = Path(bgm_path)
            if not p.exists():
                issues.append(f"BGM文件不存在: {bgm_path}")
            elif p.stat().st_size < 500000:  # 小于 500KB 不正常
                issues.append(f"BGM文件过小: {p.stat().st_size/1024:.0f}KB（生成不完整）")

    # Skill 09b HyperFrames：检查渲染结果
    elif skill_name in ("hf_render", "render"):
        mp4_path = context.get("step09b_mp4") or context.get("video_final")
        if mp4_path:
            p = Path(mp4_path)
            if not p.exists():
                issues.append(f"渲染视频不存在: {mp4_path}")
            elif p.stat().st_size < 500 * 1024:  # 小于 500KB 说明渲染质量极低
                issues.append(f"渲染视频过小: {p.stat().st_size/1024:.1f}KB（低于 500KB 门槛，渲染质量极低）")

    # Skill 11 音视频合并：检查最终文件
    elif skill_name == "audio_merge":
        final_path = context.get("final_mp4")
        if final_path:
            p = Path(final_path)
            if not p.exists():
                issues.append(f"最终视频不存在: {final_path}")
            elif p.stat().st_size < 10000:
                issues.append(f"最终视频过小: {p.stat().st_size/1024:.0f}KB（合并失败）")

    return (len(issues) == 0, issues)


# ========== Skill 12: 全维度质检 ==========

def skill12_qa(context, g2, quality_rules):
    """
    Skill 12: 全维度视觉+音画质检
    质检不通过 → 精准溯源，锁定问题节点，回滚到该节点重跑
    质检通过 → 沉淀经验，继续到 Skill 13
    """
    print("  [STEP 12] qa: 全维度质检...")

    standards = G1_CONFIG["qa_standards"]
    issues = []

    # 1. 视频文件质检
    final_video = context.get("final_mp4") or context.get("step09b_mp4")
    if final_video:
        issues.extend(qa_check_video(final_video, standards))

    # 2. HTML 视觉组件质检
    html_path = None
    hf_project = PIPELINE_ROOT / "hf_render_project"  # impl.py写入到project_root
    for h in [hf_project / "index.html", PIPELINE_ROOT / "output" / "index.html"]:
        if h.exists():
            html_path = h
            break
    if html_path:
        issues.extend(qa_check_html(html_path, standards))

    # 3. 音频文件质检
    mix_audio = PIPELINE_ROOT / "output" / "step11_mix.wav"
    voice_audio = PIPELINE_ROOT / "output" / "step05_voice.wav"
    for audio_file in [final_video, mix_audio, voice_audio]:
        p = Path(audio_file)
        if p.exists():
            size_kb = p.stat().st_size / 1024
            if size_kb < 10:
                issues.append(f"音频文件过小: {p.name} ({size_kb:.0f}KB)")

    # 4. 视觉风格质检（Shadow Cut v2）
    if standards.get("shadow_cut_v2_required") and html_path:
        try:
            html_content = Path(html_path).read_text(encoding="utf-8", errors="ignore")
            # 必须有 ghost/vignette/Impact 等组件
            has_visual_depth = (
                "ghost" in html_content and
                ("vignette" in html_content or "spotlight" in html_content) and
                "Impact" in html_content
            )
            if not has_visual_depth:
                issues.append("视觉深度不足：缺少 Shadow Cut v2 核心组件（ghost/vignette/Impact）")
        except:
            pass

    # 记录质检结果
    qa_result = {
        "time": datetime.now().isoformat(),
        "passed": len(issues) == 0,
        "issues": issues,
        "video_checked": final_video,
    }

    if issues:
        print(f"  [STEP 12] qa: 不通过 ({len(issues)} 个问题)")
        for iss in issues:
            print(f"    - {iss}")

        # 溯源：判断问题出在哪个 Skill
        problem_skill = trace_problem_skill(issues, context)
        print(f"  → 问题溯源：{problem_skill}")

        quality_rules.setdefault("past_issues", []).append(qa_result)
        save_quality_rules(quality_rules)

        return context, g2, quality_rules, False, problem_skill, issues
    else:
        print(f"  [STEP 12] qa: 通过")
        quality_rules.setdefault("past_passes", []).append(qa_result)
        save_quality_rules(quality_rules)
        return context, g2, quality_rules, True, None, []


def trace_problem_skill(issues, context):
    """精准溯源：判断问题出在哪个 Skill"""
    # 按问题特征判断来源
    for issue in issues:
        issue_lower = issue.lower()
        if "配音" in issue or "voice" in issue_lower:
            return "voice (Skill 06)"
        if "bgm" in issue_lower or "音乐" in issue:
            return "bgm (Skill 08)"
        if "渲染" in issue or "render" in issue_lower or "视频流不存在" in issue:
            return "hf_render (Skill 11)"
        if "html" in issue_lower or "视觉" in issue or "ghost" in issue_lower or "impact" in issue_lower:
            return "hf_render (Skill 11)"  # HTML 问题根源在渲染 Skill
        if "分辨率" in issue or "帧率" in issue or "编码" in issue:
            return "hf_render (Skill 11)"
        if "缺少音频" in issue or "音轨" in issue:
            return "audio_merge (Skill 11)"
        if "文件过小" in issue:
            if "rendered" in issue or "final" in issue_lower:
                return "hf_render (Skill 11)"
    return "unknown (需人工排查)"


# ========== Skill 13: 封装导出 ==========

def skill13_packaging(context, g2):
    """Skill 13: 成片封装 + 全流程源文件导出"""
    print("  [STEP 13] packaging: 封装导出...")

    project_root = PIPELINE_ROOT
    output_dir = project_root / "output"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pkg_dir = project_root / f"package_{ts}"
    pkg_dir.mkdir(exist_ok=True)

    # 收集所有产物文件
    files_to_copy = {
        "final_video": context.get("final_mp4") or context.get("step09b_mp4"),
        "html_source": (project_root / "hf_render_project" / "index.html"),
        "storyboard": (output_dir / "step09a_storyboard.json"),
        "script": (output_dir / "step03_script.json"),
        "lyrics": (output_dir / "step04_lyrics.txt"),
        "voice": (output_dir / "step05_voice.wav"),
        "whisperx": (output_dir / "whisperx_transcript.json"),
        "bgm": (output_dir / "step07_bgm.wav"),
        "mix_audio": (output_dir / "step11_mix.wav"),
    }

    copied = []
    for name, path in files_to_copy.items():
        if path:
            p = Path(path)
            if p.exists():
                dest = pkg_dir / p.name
                import shutil
                shutil.copy2(str(p), str(dest))
                copied.append(name)

    print(f"  [STEP 13] 导出完成: {len(copied)} 个文件 → {pkg_dir}")

    # 写入打包清单
    manifest = {
        "package_time": datetime.now().isoformat(),
        "topic": context.get("topic", ""),
        "files": copied,
        "package_dir": str(pkg_dir),
    }
    manifest_path = pkg_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    context["package_dir"] = str(pkg_dir)
    context["manifest"] = manifest
    return context, g2


# ========== 主流程 ==========

def main():
    parser = argparse.ArgumentParser(description="Video Factory Pipeline v25")
    parser.add_argument("--topic", type=str, default="", help="视频主题描述")
    parser.add_argument("--voice", type=str, default=None, help=f"Voice ref (default: {DEFAULT_VOICE_REF})")
    parser.add_argument("--bgm", type=str, default=None, help="BGM reference audio")
    parser.add_argument("--skip-preflight", action="store_true", help="跳过环境检查")
    parser.add_argument("--skip-bgm", action="store_true", help="跳过 BGM 生成")
    parser.add_argument("--steps", type=str, default="01-14", help="Step range, e.g. 01-14")
    parser.add_argument("--force-retry", action="store_true", help="强制从质检失败节点重跑")
    args = parser.parse_args()

    # 加载质量规则库（G2 的一部分）
    quality_rules = load_quality_rules()
    print(f"=== Video Factory Pipeline v25 ===")
    print(f"Topic: {args.topic or '(empty)'}")
    print(f"质量规则库: {len(quality_rules.get('past_issues', []))} 条历史问题 / {len(quality_rules.get('past_passes', []))} 条通过记录\n")

    if not args.skip_preflight:
        run_preflight()

    # === 治理层: 路径一致性审计 ===
    print("\n[Governance] 路径一致性审计...")
    audit_paths()

    # 初始化 G2
    g2 = G2Variables()
    g2.write("topic", args.topic, "main")
    g2.write("pipeline_start", datetime.now().isoformat(), "main")

    # 初始化 context
    voice_ref = args.voice or DEFAULT_VOICE_REF
    if not Path(voice_ref).exists():
        voice_ref = DEFAULT_VOICE_REF

    context = {
        "topic": args.topic,
        "_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "workspace": str(WORKSPACE),
        "project_root": str(PIPELINE_ROOT),
        "voice_ref": voice_ref,
        "bgm_ref": args.bgm,
        "output_dir": str(PIPELINE_ROOT / "output"),
        "pipeline_version": "v29",
        "skip_bgm": args.skip_bgm,
        "g2": g2,
    }
    Path(context["output_dir"]).mkdir(parents=True, exist_ok=True)

    # Skill 流程定义
    # (skill_name, step_num_str)
    skills_flow = [
        ("task_router",      "0"),
        ("trend_research",   "1"),
        ("verify",           "1.5"),
        ("topic_selection",  "2"),
        ("script",           "3"),
        ("lyrics",           "4"),
        ("voice",            "5"),
        ("whisperx",         "6"),
        ("bgm",              "7"),
        ("asset_fetch",      "8"),
        ("storyboard",       "9a"),
        ("hf_render",        "9b"),
        ("render",           "10"),
        ("audio_merge",       "11"),
        ("final_packaging",   "12"),
        ("qa",                "13"),
        ("delivery",          "14"),
    ]

    # 解析 step range
    try:
        start_str, end_str = args.steps.split("-")
        start_num = step_num_to_float(start_str)
        end_num = step_num_to_float(end_str)
    except:
        start_num, end_num = 1.0, 14.0

    # 逐个执行 Skill
    for skill_name, step_num_str in skills_flow:
        num = step_num_to_float(step_num_str)
        if num < start_num or num > end_num:
            continue
        if args.skip_bgm and skill_name in ("bgm", "lyrics"):
            print(f"  [STEP {step_num_str}] {skill_name}: SKIP (--skip-bgm)")
            continue

        # 不再删除storyboard.json — step09a生成的storyboard是step09b的输入
        # if step_num_str == "9b":
        #     _sb_path = PIPELINE_ROOT / "output" / "storyboard.json"
        #     if _sb_path.exists():
        #         _sb_path.unlink()
        #         print(f"  [STEP 9b] Deleted old storyboard.json for fresh generation")

        context, g2, quality_rules, ok, error = run_skill(
            skill_name, step_num_str, context, g2, quality_rules
        )

        # === 治理层: step09b产出物新鲜度校验 ===
        if ok and step_num_str == "9b":
            _comp_dir = PIPELINE_ROOT / "hf_render_project" / "compositions"
            _comp_files = list(_comp_dir.glob("beat-*.html")) if _comp_dir.exists() else []
            if not _comp_files:
                print(f"  ⚠️ [治理] step09b: compositions目录为空！渲染将使用旧文件")
            elif not check_freshness("step09b", _comp_files):
                print(f"  ⚠️ [治理] step09b: compositions是旧文件，pipeline可能回退到了旧版本")
            else:
                print(f"  ✅ [治理] step09b: {len(_comp_files)}个compositions全部是本轮新生成")

        if not ok:
            print(f"\n=== Pipeline 终止（Skill {step_num_str} 失败）===")
            print(f"错误: {error}")
            print("请修复问题后重跑，或使用 --force-retry 强制重试")
            sys.exit(1)

    # === Skill 12: 全维度质检 + 自愈回路（方案F）===
    if end_num >= 12.0 and start_num <= 12.0:
        context, g2, quality_rules, qa_passed, problem_skill, qa_issues = skill12_qa(context, g2, quality_rules)

        if not qa_passed:
            print(f"\n=== 质检不通过（进入自愈回路）===")
            print(f"问题溯源: {problem_skill}")
            print(f"质检问题: {'; '.join(qa_issues)}")

            # ── 自愈第1层：精准回滚重跑 ──────────────────────────
            rollback_map = {
                "voice (Skill 06)":           ("1", "voice",       5.0, ["voice_ref"]),
                "bgm (Skill 08)":             ("1", "bgm",         7.0, ["bgm_ref"]),
                "hf_render (Skill 11)":        ("9b", "hf_render",  9.5, ["quality"]),
                "audio_merge (Skill 11)":      ("1", "audio_merge", 11.0, ["bgm_vol", "voice_vol"]),
            }

            if problem_skill in rollback_map:
                rollback_step, rollback_name, rollback_num, degrade_keys = rollback_map[problem_skill]
                print(f"→ [自愈 L1] 精准回滚到 {rollback_name} (STEP {rollback_step})")

                for skill_name, step_num_str in skills_flow:
                    num = step_num_to_float(step_num_str)
                    if num < rollback_num:
                        continue
                    if args.skip_bgm and skill_name == "bgm":
                        continue
                    context, g2, quality_rules, ok, error = run_skill(
                        skill_name, step_num_str, context, g2, quality_rules
                    )
                    if not ok:
                        print(f"\n=== [自愈 L1] 重跑失败（Skill {step_num_str}）===")
                        # ── 自愈第2层：降级参数重跑 ──────────────────
                        print(f"→ [自愈 L2] 降级参数重试...")
                        # 降级策略
                        degrade_strategy = {
                            "hf_render (Skill 11)": {
                                "action": "降分辨率",
                                "new_context": {"_render_quality": "medium", "_render_resolution": "720p"},
                                "retry_from": 9.5,
                            },
                            "audio_merge (Skill 11)": {
                                "action": "简化音频",
                                "new_context": {"_audio_simple": True, "bgm_vol": 0.2, "voice_vol": 1.5},
                                "retry_from": 11.0,
                            },
                        }
                        if problem_skill in degrade_strategy:
                            strat = degrade_strategy[problem_skill]
                            print(f"→ [自愈 L2] 执行: {strat['action']}")
                            # 注入降级参数
                            for k, v in strat["new_context"].items():
                                context[k] = v
                            # 回滚到策略起点重跑
                            for skill_name, step_num_str in skills_flow:
                                num = step_num_to_float(step_num_str)
                                if num < strat["retry_from"]:
                                    continue
                                if args.skip_bgm and skill_name == "bgm":
                                    continue
                                context, g2, quality_rules, ok, error = run_skill(
                                    skill_name, step_num_str, context, g2, quality_rules
                                )
                                if not ok:
                                    print(f"\n=== [自愈 L2] 失败，终止 ===")
                                    sys.exit(1)
                            # 重新质检
                            context, g2, quality_rules, qa_passed, problem_skill, qa_issues = skill12_qa(
                                context, g2, quality_rules)
                            if qa_passed:
                                print("→ [自愈 L2] ✅ 成功")
                                break
                        if not qa_passed:
                            print(f"\n=== [自愈 L2] 失败，终止 ===")
                            sys.exit(1)
                        break
                else:
                    # 第1次回滚成功，重新质检
                    context, g2, quality_rules, qa_passed, problem_skill, qa_issues = skill12_qa(
                        context, g2, quality_rules)
                    if qa_passed:
                        print("→ [自愈 L1] ✅ 成功")
            else:
                print(f"无法自动回滚，请人工修复")
                print(f"质检问题详情: {qa_issues}")
                sys.exit(1)

    # === Skill 13: 封装导出 ===
    if end_num >= 13.0 and start_num <= 13.0:
        context, g2 = skill13_packaging(context, g2)

    # === Skill 14: 交付 ===
    if end_num >= 14.0 and start_num <= 14.0:
        # 查找最终视频路径，传入 context 供 skill 使用
        final_video = (
            context.get("deliver_video")
            or context.get("final_mp4")
            or context.get("step09b_mp4")
        )
        topic = context.get("topic", "视频")
        ts = context.get("_timestamp", datetime.now().strftime("%Y%m%d"))

        video_path = None
        candidates = [
            Path(final_video) if final_video else None,
            PIPELINE_ROOT / "deliverables" / f"{topic}_{ts}" / "final.mp4",
            PIPELINE_ROOT / "deliverables" / "video_unknown" / "final.mp4",
            PIPELINE_ROOT / "output" / "step11_final.mp4",
            PIPELINE_ROOT / "hf_render_project" / "rendered.mp4",
        ]
        for c in candidates:
            if c and c.exists():
                video_path = c
                break

        if video_path:
            context["final_mp4"] = str(video_path)
            context["delivery_topic"] = topic
            print(f"  [STEP 14] 视频: {video_path} ({video_path.stat().st_size//1024}KB)")

        # 调用 delivery skill（impl.py 内含飞书 API 发送逻辑）
        context, g2, quality_rules, ok, error = run_skill(
            "delivery", "14", context, g2, quality_rules
        )
        if not ok:
            print(f"\n=== [STEP 14] 交付失败: {error} ===")
        else:
            print(f"  [STEP 14] 交付完成")

    print("\n=== Pipeline Complete ===")
    print(f"Final video: {context.get('final_mp4') or context.get('step09b_mp4', 'N/A')}")


if __name__ == "__main__":
    main()
