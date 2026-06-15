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

    # 生成标题 — 不截断，保留完整主题
    title = topic if topic else "AI热点速递"

    # 从内容提取关键词作为标签
    all_text = " ".join(
        s.get("content", "") or s.get("voiceover", "") for s in sections
    )
    keywords = []
    # 提取英文关键词（项目名、公司名）
    eng_words = re.findall(r"[A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*", all_text)
    keywords.extend(eng_words[:5])
    # 提取中文高频词 — 扩充停用词表，排除口播词
    cn_words = re.findall(r"[\u4e00-\u9fff]{2,4}", all_text)
    stop_words = {
        "这个", "那个", "就是", "可以", "已经", "不是", "什么", "一个",
        "我们", "他们", "你们", "这些", "那些", "但是", "而且", "因为",
        "所以", "如果", "现在", "其实", "非常", "真的", "一下", "一下",
        "说白了", "来看", "来看", "告诉", "知道", "觉得", "还是", "就是",
        "怎么", "为什么", "多少", "几个", "然后", "接着", "首先", "其次",
        "最后", "总之", "简单", "直接", "开始", "结束", "时候", "之间",
        "上面", "下面", "前面", "后面", "左边", "右边", "里面", "外面",
        "今天", "昨天", "明天", "今年", "去年", "明年", "最近", "目前",
        "以前", "以后", "刚才", "刚刚", "马上", "立刻", "突然", "忽然",
        "可能", "也许", "大概", "或许", "肯定", "一定", "必须", "需要",
        "应该", "能够", "可以", "愿意", "想要", "打算", "准备", "计划",
        "开始", "继续", "停止", "结束", "完成", "成功", "失败", "错误",
        "问题", "答案", "方法", "方式", "情况", "状态", "结果", "效果",
        "原因", "理由", "目的", "目标", "计划", "方案", "策略", "措施",
    }
    common = [
        w for w, c in Counter(cn_words).most_common(30)
        if len(w) >= 2 and w not in stop_words
    ]
    keywords.extend(common[:5])
    # 去重
    seen = set()
    unique_keywords = []
    for k in keywords:
        if k.lower() not in seen:
            seen.add(k.lower())
            unique_keywords.append(k)
    hashtags = [f"#{k}" for k in unique_keywords[:6]]

    # 生成描述
    date_str = datetime.now().strftime("%Y年%m月%d日")
    desc_lines = [
        s.get("content", "") or s.get("voiceover", "") for s in sections[:3]
    ]
    description = (
        f"{date_str}热点速递 | " + " ".join(desc_lines)[:200] + "..."
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
