"""
asset_manager/impl.py — 素材管理器
功能：根据topic-selector的screenshot_targets，准备视频素材

职责边界：
- 读取topic-selector的screenshot_targets（需要截图的URL）
- 读取topic-selector的reference_sources（信息来源）
- 下载/截图/准备素材
- 输出到assets/目录

输入：
- output/topic_selected.json（选题信息，含screenshot_targets）
- output/step03_script.json（口播稿，了解需要什么素材）

输出：
- assets/目录下的素材文件
- output/asset_manifest.json（素材清单）
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
ASSETS_DIR = OUTPUT_DIR / "assets"
TOPIC_SELECTED_PATH = OUTPUT_DIR / "topic_selected.json"
SCRIPT_PATH = OUTPUT_DIR / "step03_script.json"
MANIFEST_PATH = OUTPUT_DIR / "asset_manifest.json"


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


def screenshot_url(url: str, output_path: str, description: str = "") -> bool:
    """截图URL（使用curl_cffi获取页面，然后用其他工具截图）"""
    try:
        from curl_cffi import requests
        
        # 获取页面内容
        resp = requests.get(url, impersonate="chrome", timeout=15)
        
        if resp.status_code == 200:
            # 保存页面内容（用于后续分析）
            html_path = output_path.replace('.png', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(resp.text)
            
            print(f"  [截图] 页面已保存: {html_path}")
            return True
        else:
            print(f"  [截图] 请求失败: {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"  [截图] Error: {e}")
        return False


def download_image(url: str, output_path: str) -> bool:
    """下载图片"""
    try:
        from curl_cffi import requests
        
        resp = requests.get(url, impersonate="chrome", timeout=15)
        
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(resp.content)
            print(f"  [下载] 图片已保存: {output_path}")
            return True
        else:
            print(f"  [下载] 请求失败: {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"  [下载] Error: {e}")
        return False


def prepare_assets(topic_selected: dict, script_data: dict) -> dict:
    """准备素材"""
    
    # 创建assets目录
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    manifest = {
        "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "topic": topic_selected.get("selected_topic", ""),
        "assets": []
    }
    
    # 1. 处理screenshot_targets
    screenshot_targets = topic_selected.get("screenshot_targets", [])
    print(f"  [素材] 截图目标: {len(screenshot_targets)} 个")
    
    for i, target in enumerate(screenshot_targets):
        url = target.get("url", "")
        description = target.get("description", "")
        purpose = target.get("purpose", "")
        
        if not url:
            continue
        
        # 生成文件名
        safe_name = re.sub(r'[^\w]', '_', description[:30]) if description else f"screenshot_{i+1}"
        output_path = str(ASSETS_DIR / f"{safe_name}.png")
        html_path = str(ASSETS_DIR / f"{safe_name}.html")
        
        print(f"  [素材] 处理截图 {i+1}: {description[:50]}...")
        
        # 截图
        success = screenshot_url(url, output_path, description)
        
        if success:
            manifest["assets"].append({
                "type": "screenshot",
                "url": url,
                "description": description,
                "purpose": purpose,
                "file_path": html_path,
                "status": "downloaded"
            })
    
    # 2. 处理reference_sources中的图片
    reference_sources = topic_selected.get("reference_sources", [])
    print(f"  [素材] 参考来源: {len(reference_sources)} 个")
    
    for i, source in enumerate(reference_sources):
        url = source.get("url", "")
        title = source.get("title", "")
        
        # 检查是否是图片URL
        if url and any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            safe_name = re.sub(r'[^\w]', '_', title[:30]) if title else f"image_{i+1}"
            output_path = str(ASSETS_DIR / f"{safe_name}.jpg")
            
            print(f"  [素材] 下载图片: {title[:50]}...")
            
            success = download_image(url, output_path)
            
            if success:
                manifest["assets"].append({
                    "type": "image",
                    "url": url,
                    "description": title,
                    "file_path": output_path,
                    "status": "downloaded"
                })
    
    # 3. 生成素材需求清单（供后续使用）
    asset_requirements = topic_selected.get("asset_requirements", {})
    
    # 截图需求
    for req in asset_requirements.get("screenshots_needed", []):
        manifest["assets"].append({
            "type": "screenshot_required",
            "description": req.get("description", ""),
            "source_url": req.get("source_url", ""),
            "purpose": req.get("purpose", ""),
            "status": "pending"
        })
    
    # 录屏需求
    for req in asset_requirements.get("recordings_needed", []):
        manifest["assets"].append({
            "type": "recording_required",
            "description": req.get("description", ""),
            "source_url": req.get("source_url", ""),
            "purpose": req.get("purpose", ""),
            "status": "pending"
        })
    
    # 素材类型需求
    for req in asset_requirements.get("stock_footage", []):
        manifest["assets"].append({
            "type": "stock_footage",
            "description": req,
            "status": "pending"
        })
    
    for req in asset_requirements.get("custom_graphics", []):
        manifest["assets"].append({
            "type": "custom_graphics",
            "description": req,
            "status": "pending"
        })
    
    return manifest


def run(context: dict) -> dict:
    """主入口：准备素材"""
    
    print(f"  [asset-manager] 开始准备素材...")
    
    load_env()
    
    # 读取选题信息
    topic_selected_path = context.get("topic_selected_path") or str(TOPIC_SELECTED_PATH)
    if not os.path.exists(topic_selected_path):
        print(f"  ❌ [asset-manager] 找不到选题文件: {topic_selected_path}")
        return context
    
    with open(topic_selected_path, "r", encoding="utf-8") as f:
        topic_selected = json.load(f)
    
    # 读取口播稿
    script_path = context.get("script_path") or str(SCRIPT_PATH)
    script_data = {}
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)
    
    print(f"  [asset-manager] 选题: {topic_selected.get('selected_topic', 'N/A')}")
    print(f"  [asset-manager] 截图目标: {len(topic_selected.get('screenshot_targets', []))} 个")
    
    # 准备素材
    manifest = prepare_assets(topic_selected, script_data)
    
    # 保存清单
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    # 统计
    downloaded = len([a for a in manifest["assets"] if a.get("status") == "downloaded"])
    pending = len([a for a in manifest["assets"] if a.get("status") == "pending"])
    
    print(f"  [asset-manager] ✅ 素材准备完成")
    print(f"    已下载: {downloaded} 个")
    print(f"    待处理: {pending} 个")
    print(f"    清单已保存到: {MANIFEST_PATH}")
    
    # 更新context
    context["asset_manifest_path"] = str(MANIFEST_PATH)
    context["asset_manifest"] = manifest
    context["assets_dir"] = str(ASSETS_DIR)
    
    return context


if __name__ == "__main__":
    test_context = {}
    result = run(test_context)
    
    print(f"\n✅ 测试完成")
    print(f"  素材数量: {len(result.get('asset_manifest', {}).get('assets', []))}")
