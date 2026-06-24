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
sys.path[:] = [p for p in sys.path if not any(x in p.lower() for x in ['hermes-agent', 'hermes_agent']) or 'core' in p.lower()]
sys.meta_path = [f for f in sys.meta_path if 'hermes' not in type(f).__module__.lower() and 'hermes' not in type(f).__name__.lower()]

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
    # 优先从 topic_selected.json 读取最新选题（避免pipeline_context.json缓存旧数据）
    topic = ""
    topic_selected_path = OUTPUT_DIR / "topic_selected.json"
    if topic_selected_path.exists():
        try:
            with open(topic_selected_path, "r", encoding="utf-8") as f:
                ts = json.load(f)
            topic = ts.get("selected_topic") or ts.get("topic", "")
        except Exception:
            pass
    if not topic:
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

    # 生成标签 — 从topic提取关键词，生成3-5个hashtag
    hashtags = []
    if topic:
        # 策略1: 整个topic作为第一个hashtag（如果长度合适）
        if len(topic) <= 20:
            hashtags.append(f"#{topic}")
        
        # 策略2: 按标点拆分，取有意义的短语
        parts = re.split(r'[，,。！？；、：:—\-\s]+', topic)
        for p in parts:
            p = p.strip()
            if len(p) >= 4 and len(p) <= 15 and f"#{p}" not in hashtags:
                hashtags.append(f"#{p}")
        
        # 策略3: 提取关键实体词
        entity_patterns = [
            r'([\u4e00-\u9fff]{2,4}(?:高考|分数线|公布|事件|事故|矿难|消防员|议员|总统|公司|企业|品牌|产品|技术))',
            r'((?:河南|河北|山东|广东|四川|浙江|江苏|北京|上海|韩国|日本|美国|中国)[\u4e00-\u9fff]{2,6})',
        ]
        for pattern in entity_patterns:
            matches = re.findall(pattern, topic)
            for m in matches:
                if f"#{m}" not in hashtags and len(m) >= 3:
                    hashtags.append(f"#{m}")
        
        # 去重保序
        seen = set()
        unique = []
        for h in hashtags:
            if h not in seen:
                seen.add(h)
                unique.append(h)
        hashtags = unique[:5]

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
