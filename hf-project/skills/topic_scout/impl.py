"""
topic_scout/impl.py — 信息采集器（v4热点列表版）
功能：从多个平台采集热点信息，去重、交叉验证，输出热点列表

职责边界：
- 并行采集多个平台的热点
- 去重：同一个热点在多个平台出现，合并成一条
- 交叉验证：多个平台都有的热点，置信度更高
- 输出热点列表（不是研究报告），供topic-selector使用

输入：无（或可选的关键词过滤）
输出：output/topic_research.json（热点列表）

输出格式：
{
  "collection_time": "2026-06-10 13:29",
  "total_collected": 103,
  "verified_topics": [
    {
      "title": "热点标题",
      "sources": ["百度热搜", "今日头条"],
      "source_urls": ["..."],
      "hot_value": 123456,
      "snippet": "热点摘要",
      "verification": {
        "cross_checked": true,
        "platforms": ["百度", "头条"],
        "confidence": 8
      }
    }
  ]
}
"""

import os
import json
import re
import warnings
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher

warnings.filterwarnings('ignore')

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
RESEARCH_PATH = OUTPUT_DIR / "topic_research.json"

# 当前年份
CURRENT_YEAR = datetime.now().year


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


def get_session():
    """获取curl_cffi会话（绕过TLS指纹检测）"""
    try:
        from curl_cffi import requests as cf_requests
        return cf_requests.Session(impersonate="chrome")
    except ImportError:
        import requests
        return requests.Session()


# ============================================================
# 热点平台采集器
# ============================================================

def fetch_baidu_hot() -> list:
    """百度热搜"""
    try:
        session = get_session()
        resp = session.get('https://top.baidu.com/board?tab=realtime', timeout=10)
        items = re.findall(r'"word":"(.*?)"', resp.text)
        if not items:
            items = re.findall(r'class="title_\w+"[^>]*>(.*?)<', resp.text)
        results = []
        for word in items[:20]:
            word = word.strip()
            if word and len(word) > 1:
                results.append({
                    "title": word,
                    "source": "百度热搜",
                    "source_url": "https://top.baidu.com/board?tab=realtime",
                    "hot_value": 0,
                })
        print(f"  [百度热搜] {len(results)} 条")
        return results
    except Exception as e:
        print(f"  [百度热搜] Error: {e}")
        return []


def fetch_toutiao_hot() -> list:
    """今日头条热榜"""
    try:
        session = get_session()
        resp = session.get('https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc', timeout=10)
        data = resp.json()
        items = data.get('data', [])
        results = []
        for item in items[:20]:
            title = item.get('Title', '')
            if title:
                results.append({
                    "title": title,
                    "source": "今日头条",
                    "source_url": item.get('Url', ''),
                    "hot_value": item.get('HotValue', 0),
                })
        print(f"  [今日头条] {len(results)} 条")
        return results
    except Exception as e:
        print(f"  [今日头条] Error: {e}")
        return []


def fetch_bilibili_hot() -> list:
    """B站热搜"""
    try:
        session = get_session()
        resp = session.get('https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all', timeout=10)
        data = resp.json()
        items = data.get('data', {}).get('list', [])
        results = []
        for item in items[:20]:
            title = item.get('title', '')
            if title:
                results.append({
                    "title": title,
                    "source": "B站热搜",
                    "source_url": f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    "hot_value": item.get('stat', {}).get('view', 0),
                })
        print(f"  [B站热搜] {len(results)} 条")
        return results
    except Exception as e:
        print(f"  [B站热搜] Error: {e}")
        return []


def fetch_douyin_hot() -> list:
    """抖音热搜"""
    try:
        session = get_session()
        resp = session.get('https://www.douyin.com/aweme/v1/web/hot/search/list/',
                          headers={'Referer': 'https://www.douyin.com/'}, timeout=10)
        data = resp.json()
        items = data.get('data', {}).get('word_list', [])
        results = []
        for item in items[:20]:
            word = item.get('word', '')
            if word:
                results.append({
                    "title": word,
                    "source": "抖音热搜",
                    "source_url": f"https://www.douyin.com/search/{word}",
                    "hot_value": item.get('hot_value', 0),
                })
        print(f"  [抖音热搜] {len(results)} 条")
        return results
    except Exception as e:
        print(f"  [抖音热搜] Error: {e}")
        return []


def fetch_v2ex_hot() -> list:
    """V2EX热帖"""
    try:
        session = get_session()
        resp = session.get('https://www.v2ex.com/api/topics/hot.json', timeout=10)
        items = resp.json()
        results = []
        for item in items[:20]:
            title = item.get('title', '')
            if title:
                results.append({
                    "title": title,
                    "source": "V2EX",
                    "source_url": item.get('url', ''),
                    "hot_value": 0,
                })
        print(f"  [V2EX] {len(results)} 条")
        return results
    except Exception as e:
        print(f"  [V2EX] Error: {e}")
        return []


def fetch_all_trending() -> list:
    """并行采集所有平台热点"""
    print("  [热点采集] 开始多平台并行采集...")
    
    all_results = []
    fetchers = [
        fetch_baidu_hot,
        fetch_toutiao_hot,
        fetch_bilibili_hot,
        fetch_douyin_hot,
        fetch_v2ex_hot,
    ]
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(f): f.__name__ for f in fetchers}
        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                print(f"  [热点采集] {futures[future]} failed: {e}")
    
    print(f"  [热点采集] 共采集 {len(all_results)} 条热点")
    return all_results


# ============================================================
# 去重和验证
# ============================================================

def similarity(a: str, b: str) -> float:
    """计算两个字符串的相似度"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate_topics(topics: list) -> list:
    """去重：相似的热点合并成一条"""
    if not topics:
        return []
    
    # 确保hot_value是数字
    for t in topics:
        hv = t.get("hot_value", 0)
        if isinstance(hv, str):
            try:
                t["hot_value"] = int(hv)
            except Exception as e:
                print(f"  ⚠️ hot_value转换失败: {e}")
                t["hot_value"] = 0
    
    # 按热度排序（高的在前）
    topics.sort(key=lambda x: x.get("hot_value", 0), reverse=True)
    
    merged = []
    used = set()
    
    for i, topic in enumerate(topics):
        if i in used:
            continue
        
        # 找相似的热点
        similar_indices = [i]
        for j in range(i + 1, len(topics)):
            if j in used:
                continue
            if similarity(topic["title"], topics[j]["title"]) > 0.6:
                similar_indices.append(j)
        
        # 合并
        sources = []
        source_urls = []
        platforms = []
        max_hot_value = topic.get("hot_value", 0)
        
        for idx in similar_indices:
            t = topics[idx]
            if t["source"] not in sources:
                sources.append(t["source"])
            if t.get("source_url") and t["source_url"] not in source_urls:
                source_urls.append(t["source_url"])
            if t["source"] not in platforms:
                platforms.append(t["source"])
            if t.get("hot_value", 0) > max_hot_value:
                max_hot_value = t["hot_value"]
            used.add(idx)
        
        # 交叉验证：多个平台都有，置信度更高
        cross_checked = len(platforms) > 1
        confidence = min(10, 5 + len(platforms) * 2) if cross_checked else 5
        
        merged.append({
            "title": topic["title"],
            "sources": sources,
            "source_urls": source_urls[:3],  # 最多保留3个URL
            "hot_value": max_hot_value,
            "snippet": topic.get("snippet", ""),
            "verification": {
                "cross_checked": cross_checked,
                "platforms": platforms,
                "confidence": confidence
            }
        })
    
    # 按置信度和热度排序
    merged.sort(key=lambda x: (x["verification"]["confidence"], x["hot_value"]), reverse=True)
    
    return merged


# ============================================================
# 主入口
# ============================================================

def run(context: dict) -> dict:
    """主入口：采集热点"""
    
    print(f"  [topic-scout] 开始采集热点...")
    print(f"  [topic-scout] 当前年份: {CURRENT_YEAR}")
    
    load_env()
    
    # 步骤1：并行采集
    print(f"  [topic-scout] 步骤1: 多平台并行采集...")
    all_topics = fetch_all_trending()
    
    # 步骤2：去重
    print(f"  [topic-scout] 步骤2: 去重...")
    verified_topics = deduplicate_topics(all_topics)
    
    print(f"  [topic-scout] 去重后: {len(verified_topics)} 个独立热点")
    
    # 步骤3：构建输出
    output = {
        "collection_time": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "total_collected": len(all_topics),
        "total_verified": len(verified_topics),
        "verified_topics": verified_topics
    }
    
    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESEARCH_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"  [topic-scout] ✅ 采集完成")
    print(f"    原始采集: {len(all_topics)} 条")
    print(f"    去重后: {len(verified_topics)} 个热点")
    print(f"    交叉验证: {len([t for t in verified_topics if t['verification']['cross_checked']])} 个")
    print(f"    已保存到: {RESEARCH_PATH}")
    
    # 更新context
    context["research_path"] = str(RESEARCH_PATH)
    context["research_data"] = output
    context["topic_count"] = len(verified_topics)
    
    return context


if __name__ == "__main__":
    test_context = {}
    result = run(test_context)
    
    print(f"\n✅ 测试完成")
    print(f"  热点数量: {result.get('topic_count')}")
