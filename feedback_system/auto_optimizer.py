"""
auto_optimizer.py — 自动优化模块
功能：根据失败案例优化prompt和参数
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

# 配置路径
CONFIG_PATH = Path(__file__).parent / "config.json"
LOG_DIR = Path(__file__).parent / "logs" / "optimization_history"

class AutoOptimizer:
    def __init__(self):
        self.config = self.load_config()
        self.history_file = LOG_DIR / f"optimization_{datetime.now().strftime('%Y%m%d')}.json"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.history = self.load_history()
    
    def load_config(self):
        """加载配置"""
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_history(self):
        """加载优化历史"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"optimizations": []}
    
    def save_history(self):
        """保存优化历史"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
    
    def analyze_failure_patterns(self, quality_report):
        """分析失败模式"""
        patterns = Counter()
        details = {}
        
        for issue in quality_report.get("issues", []):
            for issue_desc in issue.get("issues", []):
                # 分类问题
                if "CSS opacity:0" in issue_desc:
                    patterns["css_opacity"] += 1
                    details.setdefault("css_opacity", []).append(issue)
                elif "内容不足" in issue_desc or "过短" in issue_desc:
                    patterns["content_insufficient"] += 1
                    details.setdefault("content_insufficient", []).append(issue)
                elif "风格不符合" in issue_desc:
                    patterns["style_mismatch"] += 1
                    details.setdefault("style_mismatch", []).append(issue)
                elif "禁止词汇" in issue_desc:
                    patterns["forbidden_words"] += 1
                    details.setdefault("forbidden_words", []).append(issue)
                elif "缺少" in issue_desc:
                    patterns["missing_elements"] += 1
                    details.setdefault("missing_elements", []).append(issue)
                else:
                    patterns["other"] += 1
                    details.setdefault("other", []).append(issue)
        
        return dict(patterns), details
    
    def generate_optimization_prompt(self, skill_name, failure_patterns, failure_details):
        """根据失败模式生成优化prompt"""
        optimizations = []
        
        if skill_name == "hf_builder":
            if failure_patterns.get("css_opacity", 0) > 0:
                optimizations.append("""
## ⚠️ 重要：绝对不要在CSS中设置opacity:0！

错误写法：
<div style="opacity: 0;"> ← 这样会导致渲染器看不到内容！

正确写法：
- 元素默认可见（不设置opacity）
- 用GSAP的tl.set()设置初始状态
- 用tl.from()做入场动画
""")
            
            if failure_patterns.get("content_insufficient", 0) > 0:
                optimizations.append("""
## ⚠️ 内容必须丰富！

要求：
- 6-8+ 个可见元素
- 标题(80-120px+发光)
- 数据卡片(圆角+边框+大字号数字)
- 进度条、标签pill、装饰层
- 每个场景至少2-3个装饰层
""")
        
        elif skill_name == "script_writer":
            if failure_patterns.get("style_mismatch", 0) > 0:
                optimizations.append("""
## ⚠️ 必须使用标志性表达！

必须包含以下至少一个：
- 你品
- 说白了
- 真相是
- 细品
- 别被忽悠了
- 我翻遍全网
""")
            
            if failure_patterns.get("forbidden_words", 0) > 0:
                optimizations.append("""
## ⚠️ 绝对禁止以下词汇！

禁止：
- 值得注意的是
- 需要指出的是
- 首先...其次...最后
- 总而言之
- 宝子们、家人们
""")
        
        return "\n".join(optimizations)
    
    def optimize_skill(self, skill_name, quality_report):
        """优化指定skill"""
        self.log(f"开始优化 {skill_name}...")
        
        # 分析失败模式
        patterns, details = self.analyze_failure_patterns(quality_report)
        
        if not patterns:
            self.log(f"✅ {skill_name} 无需优化")
            return None
        
        # 生成优化prompt
        optimization = self.generate_optimization_prompt(skill_name, patterns, details)
        
        if optimization:
            # 记录优化历史
            record = {
                "timestamp": datetime.now().isoformat(),
                "skill": skill_name,
                "patterns": patterns,
                "optimization": optimization[:500]  # 截断
            }
            self.history["optimizations"].append(record)
            self.save_history()
            
            self.log(f"✅ {skill_name} 优化完成")
            return optimization
        
        return None
    
    def get_optimization_hints(self, skill_name):
        """获取优化提示（从历史中学习）"""
        hints = []
        
        # 从历史中提取该skill的常见问题
        skill_history = [
            opt for opt in self.history.get("optimizations", [])
            if opt.get("skill") == skill_name
        ]
        
        if skill_history:
            # 统计常见问题
            all_patterns = Counter()
            for opt in skill_history:
                for pattern, count in opt.get("patterns", {}).items():
                    all_patterns[pattern] += count
            
            # 生成提示
            for pattern, count in all_patterns.most_common(3):
                if pattern == "css_opacity":
                    hints.append("历史问题：CSS opacity:0过多")
                elif pattern == "content_insufficient":
                    hints.append("历史问题：内容不足")
                elif pattern == "style_mismatch":
                    hints.append("历史问题：风格不符合")
                elif pattern == "forbidden_words":
                    hints.append("历史问题：包含禁止词汇")
        
        return hints
    
    def should_retry(self, skill_name, attempt, quality_report):
        """判断是否应该重试"""
        checkpoint = self.config.get("quality_checkpoints", {}).get(skill_name, {})
        max_retries = checkpoint.get("max_retries", 3)
        
        if attempt >= max_retries:
            return False
        
        # 检查质量分数
        threshold = checkpoint.get("threshold", 0.8)
        patterns, _ = self.analyze_failure_patterns(quality_report)
        
        # 如果有严重问题，可以重试
        if patterns.get("css_opacity", 0) > 0:
            return True
        if patterns.get("content_insufficient", 0) > 0:
            return True
        
        return False


# 全局实例
_optimizer = None

def get_optimizer():
    global _optimizer
    if _optimizer is None:
        _optimizer = AutoOptimizer()
    return _optimizer

def optimize_skill(skill_name, quality_report):
    return get_optimizer().optimize_skill(skill_name, quality_report)

def get_optimization_hints(skill_name):
    return get_optimizer().get_optimization_hints(skill_name)

def should_retry(skill_name, attempt, quality_report):
    return get_optimizer().should_retry(skill_name, attempt, quality_report)


if __name__ == "__main__":
    # 测试
    optimizer = AutoOptimizer()
    
    # 模拟质量报告
    test_report = {
        "issues": [
            {
                "skill": "hf_builder",
                "issues": ["CSS opacity:0存在: 5个", "可见内容不足: 2 < 3"]
            },
            {
                "skill": "script_writer",
                "issues": ["风格不符合：缺少标志性表达"]
            }
        ]
    }
    
    # 分析失败模式
    patterns, details = optimizer.analyze_failure_patterns(test_report)
    print(f"\n失败模式: {patterns}")
    
    # 优化hf_builder
    optimization = optimizer.optimize_skill("hf_builder", test_report)
    if optimization:
        print(f"\n优化建议:\n{optimization}")
