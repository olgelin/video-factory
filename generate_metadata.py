"""
generate_metadata.py — 视频元数据生成器
输出: metadata.json (标题+标签+描述)
"""
import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

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

    # 生成标题
    title = topic[:30] if topic else "AI热点速递"

    # 从内容提取关键词作为标签
    all_text = " ".join(
        s.get("content", "") or s.get("voiceover", "") for s in sections
    )
    keywords = []
    # 提取英文关键词（项目名、公司名）
    eng_words = re.findall(r"[A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*", all_text)
    keywords.extend(eng_words[:3])
    # 提取中文高频词
    cn_words = re.findall(r"[\u4e00-\u9fff]{2,4}", all_text)
    stop_words = {"这个", "那个", "就是", "可以", "已经", "不是", "什么", "一个",
                  "我们", "他们", "你们", "这些", "那些", "但是", "而且", "因为",
                  "所以", "如果", "现在", "其实", "非常", "真的", "一下"}
    common = [
        w for w, c in Counter(cn_words).most_common(20)
        if len(w) >= 2 and w not in stop_words
    ]
    keywords.extend(common[:3])
    hashtags = [f"#{k}" for k in keywords[:4]]

    # 生成描述
    date_str = datetime.now().strftime("%Y年%m月%d日")
    desc_lines = [
        s.get("content", "") or s.get("voiceover", "") for s in sections[:3]
    ]
    description = (
        f"{date_str}热点速递 | " + " ".join(desc_lines)[:100] + "..."
    )

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
