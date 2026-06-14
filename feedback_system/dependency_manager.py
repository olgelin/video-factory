"""
dependency_manager.py — 依赖版本管理模块
功能：检测、更新、回滚核心依赖
"""

import json
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime
import re

# 配置路径
CONFIG_PATH = Path(__file__).parent / "config.json"
LOG_DIR = Path(__file__).parent / "logs" / "dependency_updates"

class DependencyManager:
    def __init__(self):
        self.config = self.load_config()
        self.log_file = LOG_DIR / f"updates_{datetime.now().strftime('%Y%m%d')}.log"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    def load_config(self):
        """加载配置"""
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_config(self):
        """保存配置"""
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")
    
    def get_pip_version(self, package_name):
        """获取pip包当前版本"""
        try:
            result = subprocess.run(
                f"pip show {package_name}",
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':')[1].strip()
        except Exception as e:
            self.log(f"获取pip版本失败: {e}")
        return None
    
    def get_npm_version(self, package_name):
        """获取npm包当前版本"""
        try:
            result = subprocess.run(
                f"npm list -g {package_name} --depth=0",
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                match = re.search(r'@(\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            self.log(f"获取npm版本失败: {e}")
        return None
    
    def get_latest_pypi_version(self, package_name):
        """获取PyPI最新版本"""
        try:
            result = subprocess.run(
                f"pip index versions {package_name}",
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                match = re.search(r'INSTALLED:.*?LATEST:(.*?)(?:\s|$)', result.stdout)
                if match:
                    return match.group(1).strip()
        except Exception as e:
            self.log(f"获取PyPI版本失败: {e}")
        return None
    
    def get_latest_npm_version(self, package_name):
        """获取npm最新版本"""
        try:
            result = subprocess.run(
                f"npm show {package_name} version",
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            self.log(f"获取npm版本失败: {e}")
        return None
    
    def check_updates(self):
        """检查所有依赖的更新"""
        updates = []
        
        for dep_name, dep_info in self.config["dependencies"].items():
            current = dep_info["current_version"]
            package = dep_info["package_name"]
            method = dep_info["update_method"]
            
            # 获取当前安装版本
            if method == "pip":
                installed = self.get_pip_version(package)
                latest = self.get_latest_pypi_version(package)
            else:
                installed = self.get_npm_version(package)
                latest = self.get_latest_npm_version(package)
            
            if latest and installed and latest != installed:
                updates.append({
                    "name": dep_name,
                    "package": package,
                    "installed": installed,
                    "latest": latest,
                    "method": method
                })
                self.log(f"⚠️ {dep_name} 有新版本: {installed} → {latest}")
        
        return updates
    
    def backup_current(self, dep_name):
        """备份当前版本"""
        dep_info = self.config["dependencies"][dep_name]
        package = dep_info["package_name"]
        method = dep_info["update_method"]
        
        if method == "pip":
            current = self.get_pip_version(package)
        else:
            current = self.get_npm_version(package)
        
        # 保存到配置
        dep_info["backup_version"] = current
        self.save_config()
        
        self.log(f"✅ 已备份 {dep_name} 版本: {current}")
        return current
    
    def update_dependency(self, dep_name, version=None):
        """更新依赖"""
        dep_info = self.config["dependencies"][dep_name]
        package = dep_info["package_name"]
        method = dep_info["update_method"]
        
        # 备份当前版本
        self.backup_current(dep_name)
        
        # 更新
        if version:
            target = version
        else:
            if method == "pip":
                target = self.get_latest_pypi_version(package)
            else:
                target = self.get_latest_npm_version(package)
        
        if not target:
            self.log(f"❌ 无法获取 {dep_name} 最新版本")
            return False
        
        self.log(f"🔄 更新 {dep_name} 到 {target}...")
        
        if method == "pip":
            cmd = f"pip install {package}=={target}"
        else:
            cmd = f"npm install -g {package}@{target}"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # 更新配置
            dep_info["current_version"] = target
            self.save_config()
            self.log(f"✅ {dep_name} 更新成功: {target}")
            return True
        else:
            self.log(f"❌ {dep_name} 更新失败: {result.stderr[:200]}")
            return False
    
    def rollback(self, dep_name):
        """回滚到备份版本"""
        dep_info = self.config["dependencies"][dep_name]
        backup = dep_info.get("backup_version")
        
        if not backup:
            self.log(f"❌ 无备份版本可回滚: {dep_name}")
            return False
        
        self.log(f"🔄 回滚 {dep_name} 到 {backup}...")
        return self.update_dependency(dep_name, backup)
    
    def verify_update(self, dep_name):
        """验证更新是否成功"""
        dep_info = self.config["dependencies"][dep_name]
        package = dep_info["package_name"]
        method = dep_info["update_method"]
        expected = dep_info["current_version"]
        
        if method == "pip":
            actual = self.get_pip_version(package)
        else:
            actual = self.get_npm_version(package)
        
        if actual == expected:
            self.log(f"✅ 验证通过: {dep_name} = {actual}")
            return True
        else:
            self.log(f"❌ 验证失败: {dep_name} 期望 {expected}, 实际 {actual}")
            return False
    
    def check_and_update_all(self):
        """检查并更新所有依赖"""
        self.log("=" * 50)
        self.log("开始检查依赖更新")
        self.log("=" * 50)
        
        updates = self.check_updates()
        
        if not updates:
            self.log("✅ 所有依赖都是最新版本")
            return []
        
        results = []
        for update in updates:
            dep_name = update["name"]
            latest = update["latest"]
            
            # 更新
            if self.update_dependency(dep_name, latest):
                # 验证
                if self.verify_update(dep_name):
                    results.append({
                        "name": dep_name,
                        "status": "success",
                        "version": latest
                    })
                else:
                    # 回滚
                    self.rollback(dep_name)
                    results.append({
                        "name": dep_name,
                        "status": "failed_rollback",
                        "version": latest
                    })
            else:
                results.append({
                    "name": dep_name,
                    "status": "failed",
                    "version": latest
                })
        
        self.log("=" * 50)
        self.log(f"更新完成: {len([r for r in results if r['status'] == 'success'])} 成功, "
                 f"{len([r for r in results if r['status'] != 'success'])} 失败")
        self.log("=" * 50)
        
        return results


# 全局实例
_manager = None

def get_manager():
    global _manager
    if _manager is None:
        _manager = DependencyManager()
    return _manager

def check_updates():
    return get_manager().check_updates()

def update_all():
    return get_manager().check_and_update_all()

def rollback(dep_name):
    return get_manager().rollback(dep_name)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="依赖版本管理")
    parser.add_argument("--check", action="store_true", help="检查更新")
    parser.add_argument("--update", action="store_true", help="更新所有")
    parser.add_argument("--rollback", type=str, help="回滚指定依赖")
    
    args = parser.parse_args()
    
    if args.check:
        updates = check_updates()
        if updates:
            print(f"\n发现 {len(updates)} 个更新:")
            for u in updates:
                print(f"  - {u['name']}: {u['installed']} → {u['latest']}")
        else:
            print("\n所有依赖都是最新版本")
    elif args.update:
        results = update_all()
        if results:
            print("\n更新结果:")
            for r in results:
                print(f"  - {r['name']}: {r['status']}")
    elif args.rollback:
        rollback(args.rollback)
    else:
        parser.print_help()
