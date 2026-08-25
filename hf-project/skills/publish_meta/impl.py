"""
publish_meta/impl.py — 发布元数据生成（标题/描述/标签）

功能：视频制作完成后，根据口播脚本 + 选题信息，生成发布用的元数据：
- title：标题（≤16字）
- description：描述（≤40字）
- tags：标签（4个）

输入：
- output/step03_script.json（口播脚本）
- output/topic_selected.json（选题信息）

输出：output/publish_meta.json
"""

import os
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from llm_utils import call_llm

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
SCRIPT_PATH = OUTPUT_DIR / "step03_script.json"
TOPIC_SELECTED_PATH = OUTPUT_DIR / "topic_selected.json"
META_PATH = OUTPUT_DIR / "publish_meta.json"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    p = _PROMPTS_DIR / f"{name}.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def _parse_json(response: str):
    """多层解析 JSON，失败返回 None"""
    cleaned = re.sub(r'```json\s*', '', response)
    cleaned = re.sub(r'```\s*$', '', cleaned).strip()
    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        try:
            fixed = re.sub(r',\s*}', '}', m.group())
            fixed = re.sub(r',\s*]', ']', fixed)
            return json.loads(fixed)
        except Exception:
            return None


def run(context: dict) -> dict:
    """主入口：生成发布元数据"""
    print("  [publish-meta] 生成发布元数据（标题/描述/标签）...")

    # 读取脚本
    script_path = context.get("script_path") or str(SCRIPT_PATH)
    if not os.path.exists(script_path):
        print(f"  ❌ [publish-meta] 找不到脚本: {script_path}")
        return context
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    topic = script.get("topic", "")
    sections = script.get("voiceover_sections", []) or script.get("scenes", [])
    full_text = "\n".join(
        s.get("content", "") or s.get("voiceover", "") for s in sections
    )

    # 读取选题信息
    angle = ""
    hook = ""
    tp = context.get("topic_selected_path") or str(TOPIC_SELECTED_PATH)
    if os.path.exists(tp):
        try:
            with open(tp, "r", encoding="utf-8") as f:
                ts = json.load(f)
            angle = ts.get("angle", "")
            hook = ts.get("hook", "")
        except Exception:
            pass

    system_prompt = _load_prompt("system")
    prompt = f"""话题：{topic}
切入角度：{angle}
开头hook：{hook}

口播文案：
{full_text[:1500]}

请根据以上内容生成发布元数据（标题/描述/标签），输出JSON。"""

    response = call_llm(prompt, system_prompt, max_tokens=800, task="creative")
    if not response:
        print("  ❌ [publish-meta] LLM 返回为空")
        return context

    meta = _parse_json(response)
    if not meta:
        print("  ⚠️ [publish-meta] JSON 解析失败，跳过")
        return context

    # 字段校验 + 长度兜底
    title = (meta.get("title") or "").strip()
    description = (meta.get("description") or "").strip()
    tags = meta.get("tags") or []

    # 标题 ≤16 字，描述 ≤40 字（超长硬截断）
    title = title[:16]
    description = description[:40]

    # 标签正好 4 个（不足补空，超出截断）
    tags = [str(t).strip() for t in tags if str(t).strip()]
    while len(tags) < 4:
        tags.append("")
    tags = tags[:4]

    meta = {
        "topic": topic,
        "title": title,
        "description": description,
        "tags": tags,
    }

    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    context["publish_meta_path"] = str(META_PATH)
    context["publish_meta"] = meta

    print(f"  [publish-meta] ✅ 标题: {title}")
    print(f"  [publish-meta] ✅ 描述: {description}")
    print(f"  [publish-meta] ✅ 标签: {' | '.join(tags)}")
    return context


if __name__ == "__main__":
    result = run({})
    print(f"\n✅ 测试完成")
    print(f"  元数据: {result.get('publish_meta')}")
