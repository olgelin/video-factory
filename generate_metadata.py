"""
generate_metadata.py - 视频元数据生成器
输出: metadata.json (标题+标签+描述)
"""
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# 清除PYTHONPATH防止hermes-agent/venv干扰
if 'PYTHONPATH' in os.environ:
    del os.environ['PYTHONPATH']
sys.path[:] = [p for p in sys.path if 'hermes-agent' not in p.lower() or 'core' in p.lower()]

# 预加载.env，确保llm_utils模块级代码能读到API key
try:
    from dotenv import load_dotenv
    for env_path in [os.path.join(os.environ.get('HERMES_HOME', ''), '.env'),
                     os.path.join(os.path.expanduser('~'), '.hermes', '.env')]:
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)
            break
except Exception:
    pass

OUTPUT_DIR = Path(__file__).parent / "hf-project" / "output"


def generate_metadata(context: dict) -> dict:
    """生成视频元数据（标题+标签+描述）"""
    topic = context.get("topic", "")
    script_path = OUTPUT_DIR / "step03_script.json"

    # 从脚本提取内容摘要
    sections = []
    if script_path.exists():
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                script = json.load(f)
            sections = script.get("voiceover_sections", script.get("scenes", []))
        except Exception:
            pass

    # 生成标题 — 不截断，保留完整主题
    title = topic if topic else "AI热点速递"

    # 从topic提取关键词作为标签（jieba分词，确定性输出）
    hashtags = []
    if topic:
        try:
            import jieba
            words = list(jieba.cut(topic))
        except Exception:
            # fallback: 按标点拆分
            words = re.split(r'[：:、，,；!！?？\-—\s\d]+', topic)
        # 过滤：去掉单字、纯数字、虚词、jieba误切的2字组合
        stop_chars = set('的了在是和与为及或从把被让将就才刚只每也还都没不过对什么')
        meaningful = []
        for w in words:
            w = w.strip()
            if len(w) < 2 or re.match(r'^\d+$', w) or w in stop_chars:
                continue
            # 2字词只保留已知实体词（jieba常把新词切成2字乱码）
            if len(w) == 2 and not re.match(r'^(?:美国|中国|日本|韩国|欧盟|采购|辟谣|谣言|真相|资质|行业|企业|产品|技术|市场|经济|政策|改革|制裁|关税|芯片|汽车|车企|补贴|破产|退市|召回|造假)$', w):
                continue
            meaningful.append(w)
        # 组合：国家+实体（如"美国"+"企业"→"美国企业"）
        combined = []
        i = 0
        while i < len(meaningful):
            # 如果当前词是国家/地区名，尝试与下一个词组合
            if i + 1 < len(meaningful) and re.match(r'^(?:中国|美国|日本|韩国|欧盟|俄罗斯|印度|英国|法国|德国)$', meaningful[i]):
                combined.append(meaningful[i] + meaningful[i+1])
                i += 2
            else:
                combined.append(meaningful[i])
                i += 1
        # 去重保序
        seen = set()
        unique = []
        for k in combined:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        hashtags = [f"#{k}" for k in unique[:6]]

    # 生成描述 — hook风格，前3句口播精华
    date_str = datetime.now().strftime("%Y年%m月%d日")
    desc_lines = []
    for s in sections[:3]:
        text = s.get("content", "") or s.get("voiceover", "")
        if text:
            desc_lines.append(text[:80])
    hook = " | ".join(desc_lines) if desc_lines else topic
    description = f"{date_str}热点速递 | {hook}..."

    metadata = {
        "title": title,
        "hashtags": hashtags,
        "description": description,
        "generated_at": datetime.now().isoformat(),
        "duration": context.get("voice_duration", 0),
        "video_path": str(context.get("mixed_path", "")),
    }

    # 保存
    meta_path = OUTPUT_DIR / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return metadata


if __name__ == "__main__":
    ctx_path = OUTPUT_DIR / "pipeline_context.json"
    if ctx_path.exists():
        with open(ctx_path, "r", encoding="utf-8") as f:
            ctx = json.load(f)
        result = generate_metadata(ctx)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("No pipeline_context.json found")
