"""
asset_collector/impl.py — 素材采集模块
功能：采集截图、录屏等素材，用于画中画展示
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
ASSETS_DIR = OUTPUT_DIR / "assets"

class AssetCollector:
    def __init__(self):
        self.assets_dir = ASSETS_DIR
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.assets = []
    
    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"  [{timestamp}] [{level}] {message}")
    
    def capture_screenshot(self, url, name, width=1920, height=1080):
        """截取网页截图"""
        self.log(f"截取截图: {name} from {url}")
        
        output_path = self.assets_dir / f"{name}.png"
        
        # 使用puppeteer截图（通过node脚本）
        script = f"""
const puppeteer = require('puppeteer');

(async () => {{
    const browser = await puppeteer.launch({{
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }});
    const page = await browser.newPage();
    await page.setViewport({{ width: {width}, height: {height} }});
    await page.goto('{url}', {{ waitUntil: 'networkidle2' }});
    await page.screenshot({{ path: '{output_path}', fullPage: false }});
    await browser.close();
}})();
"""
        
        script_path = self.assets_dir / f"capture_{name}.js"
        script_path.write_text(script)
        
        try:
            result = subprocess.run(
                f"node {script_path}",
                shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and output_path.exists():
                self.log(f"✅ 截图成功: {output_path}")
                self.assets.append({
                    "type": "screenshot",
                    "name": name,
                    "path": str(output_path),
                    "url": url,
                    "timestamp": datetime.now().isoformat()
                })
                return str(output_path)
            else:
                self.log(f"❌ 截图失败: {result.stderr[:200]}", "WARN")
        except Exception as e:
            self.log(f"❌ 截图异常: {e}", "WARN")
        
        # 清理临时脚本
        script_path.unlink(missing_ok=True)
        return None
    
    def add_manual_asset(self, file_path, name=None, asset_type="image"):
        """添加手动准备的素材"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.log(f"❌ 文件不存在: {file_path}", "WARN")
            return None
        
        # 复制到assets目录
        if name is None:
            name = file_path.stem
        
        ext = file_path.suffix
        dest_path = self.assets_dir / f"{name}{ext}"
        
        import shutil
        shutil.copy2(file_path, dest_path)
        
        self.log(f"✅ 添加素材: {dest_path}")
        
        asset_info = {
            "type": asset_type,
            "name": name,
            "path": str(dest_path),
            "original_path": str(file_path),
            "timestamp": datetime.now().isoformat()
        }
        self.assets.append(asset_info)
        
        return str(dest_path)
    
    def get_assets_for_scene(self, scene_id, topic_keywords):
        """为指定场景获取相关素材"""
        # 根据场景ID和关键词筛选素材
        relevant_assets = []
        
        for asset in self.assets:
            # 简单匹配：检查素材名称是否包含关键词
            asset_name = asset["name"].lower()
            for keyword in topic_keywords:
                if keyword.lower() in asset_name:
                    relevant_assets.append(asset)
                    break
        
        # 如果没有匹配的，返回前几个素材
        if not relevant_assets and self.assets:
            relevant_assets = self.assets[:2]
        
        return relevant_assets
    
    def generate_asset_manifest(self):
        """生成素材清单"""
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "total_assets": len(self.assets),
            "assets": self.assets
        }
        
        manifest_path = self.assets_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        self.log(f"✅ 素材清单已生成: {manifest_path}")
        return manifest


def run(context: dict) -> dict:
    """主入口：素材采集"""
    self.log = lambda msg, level="INFO": print(f"  [asset-collector] {msg}")
    
    topic = context.get("topic", "")
    self.log(f"开始采集素材: {topic}")
    
    collector = AssetCollector()
    
    # 检查是否有手动准备的素材
    manual_assets_dir = Path(__file__).parent.parent.parent / "manual_assets"
    if manual_assets_dir.exists():
        self.log(f"发现手动素材目录: {manual_assets_dir}")
        for asset_file in manual_assets_dir.glob("*"):
            if asset_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.mp4', '.webm']:
                asset_type = "video" if asset_file.suffix.lower() in ['.mp4', '.webm'] else "image"
                collector.add_manual_asset(asset_file, asset_type=asset_type)
    
    # 生成素材清单
    manifest = collector.generate_asset_manifest()
    
    # 更新context
    context["assets_dir"] = str(ASSETS_DIR)
    context["assets_manifest"] = manifest
    context["assets_count"] = len(collector.assets)
    
    self.log(f"✅ 素材采集完成: {len(collector.assets)} 个素材")
    
    return context


if __name__ == "__main__":
    # 测试
    collector = AssetCollector()
    
    # 添加测试素材
    test_assets = [
        ("test_image.png", "image"),
        ("test_video.mp4", "video")
    ]
    
    for name, asset_type in test_assets:
        test_path = Path(f"/tmp/{name}")
        if test_path.exists():
            collector.add_manual_asset(test_path, asset_type=asset_type)
    
    # 生成清单
    manifest = collector.generate_asset_manifest()
    print(f"\n素材清单: {manifest}")
