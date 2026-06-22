"""
generate_metadata.py — 视频元数据生成器
输出: metadata.json (标题+标签+描述)
"""
import json
import re
from pathlib import Path
from datetime import datetime

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

    # 从topic提取关键词作为标签（用LLM生成，精准高效）
    hashtags = []
    if topic:
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent / "hf-project"))
            from llm_utils import call_llm
            tag_prompt = f"""为以下短视频话题生成6个精准的中文标签（带#号），要求：
- 每个标签2-4个字
- 包含核心实体（人名/公司名/产品名/行业术语）
- 不要废话，直接输出JSON数组

话题：{topic}

输出格式：["#标签1","#标签2",...]"""
            tag_response = call_llm(tag_prompt, max_tokens=200)
            if tag_response:
                # 清理并解析JSON
                cleaned = tag_response.strip()
                if cleaned.startswith('['):
                    tags = __import__('json').loads(cleaned)
                    hashtags = [t if t.startswith('#') else f'#{t}' for t in tags[:6]]
        except Exception:
            pass
    # fallback: 如果LLM失败，用标点拆分取完整短语
    if not hashtags and topic:
        # 提取英文
        eng = re.findall(r'[A-Za-z][\w.-]+', topic)[:2]
        # 提取中文：用标点拆分后取完整短语（不再截断）
        cn_only = re.sub(r'[A-Za-z0-9]+', '', topic)
        parts = re.split(r'[：:、，,；!！?？\-—\s]+', cn_only)
        cn = []
        for p in parts:
            p = p.strip()
            if len(p) >= 2 and len(p) <= 8 and not re.match(r'^[与的和在为及或从把被让将已还没也不就才刚只每]', p):
                cn.append(p)  # 不截断，保持完整语义
        keywords = eng + cn[:4]
        hashtags = [f"#{k}" for k in dict.fromkeys(keywords)][:6]

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
