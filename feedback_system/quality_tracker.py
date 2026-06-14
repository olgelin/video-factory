"""
quality_tracker.py — 全链路质量追溯模块
功能：追溯每个skill的质量问题，定位根因
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

# 配置路径
CONFIG_PATH = Path(__file__).parent / "config.json"
LOG_DIR = Path(__file__).parent / "logs" / "quality_reports"

class QualityTracker:
    def __init__(self):
        self.config = self.load_config()
        self.report_file = LOG_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.issues = []
    
    def load_config(self):
        """加载配置"""
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
    
    def check_topic_quality(self, topic_data):
        """检查选题质量"""
        score = 1.0
        issues = []
        
        # 检查必要字段
        if not topic_data.get("selected_topic"):
            score -= 0.3
            issues.append("缺少selected_topic")
        
        if not topic_data.get("angle"):
            score -= 0.2
            issues.append("缺少angle")
        
        if not topic_data.get("hook"):
            score -= 0.2
            issues.append("缺少hook")
        
        if not topic_data.get("key_points"):
            score -= 0.2
            issues.append("缺少key_points")
        
        return max(0, score), issues
    
    def check_script_quality(self, script_data):
        """检查脚本质量"""
        score = 1.0
        issues = []
        
        # 检查段落数量
        sections = script_data.get("voiceover_sections", [])
        if len(sections) < 6:
            score -= 0.2
            issues.append(f"段落不足: {len(sections)} < 6")
        
        # 检查风格符合
        full_text = " ".join([s.get("content", "") for s in sections])
        style_markers = ["你品", "说白了", "真相是", "细品", "别被忽悠了"]
        if not any(marker in full_text for marker in style_markers):
            score -= 0.3
            issues.append("风格不符合：缺少标志性表达")
        
        # 检查字数
        total_chars = len(full_text)
        if total_chars < 400:
            score -= 0.2
            issues.append(f"字数不足: {total_chars} < 400")
        
        # 检查禁止词汇
        forbidden = ["值得注意的是", "需要指出的是", "首先", "其次", "最后", "宝子们"]
        for word in forbidden:
            if word in full_text:
                score -= 0.1
                issues.append(f"包含禁止词汇: {word}")
        
        return max(0, score), issues
    
    def check_voice_quality(self, voice_path):
        """检查配音质量"""
        score = 1.0
        issues = []
        
        if not os.path.exists(voice_path):
            return 0, ["配音文件不存在"]
        
        # 检查文件大小
        size = os.path.getsize(voice_path)
        if size < 1000:
            score -= 0.5
            issues.append(f"配音文件过小: {size} bytes")
        
        # 检查时长（通过ffprobe）
        try:
            import subprocess
            result = subprocess.run(
                f'ffprobe -v quiet -show_entries format=duration -of json "{voice_path}"',
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data["format"]["duration"])
                if duration < 30:
                    score -= 0.3
                    issues.append(f"配音时长过短: {duration}s < 30s")
        except Exception as e:
            self.log(f"检查配音时长失败: {e}", "WARN")
        
        return max(0, score), issues
    
    def check_bgm_quality(self, bgm_path):
        """检查BGM质量"""
        score = 1.0
        issues = []
        
        if not os.path.exists(bgm_path):
            return 0, ["BGM文件不存在"]
        
        # 检查文件大小
        size = os.path.getsize(bgm_path)
        if size < 10000:
            score -= 0.5
            issues.append(f"BGM文件过小: {size} bytes")
        
        # 检查时长
        try:
            import subprocess
            result = subprocess.run(
                f'ffprobe -v quiet -show_entries format=duration -of json "{bgm_path}"',
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data["format"]["duration"])
                if duration < 60:
                    score -= 0.3
                    issues.append(f"BGM时长过短: {duration}s < 60s")
        except Exception as e:
            self.log(f"检查BGM时长失败: {e}", "WARN")
        
        return max(0, score), issues
    
    def check_storyboard_quality(self, storyboard_data):
        """检查storyboard质量"""
        score = 1.0
        issues = []
        
        # 检查场景数量
        scenes = storyboard_data if isinstance(storyboard_data, list) else storyboard_data.get("scenes", [])
        if len(scenes) < 6:
            score -= 0.2
            issues.append(f"场景不足: {len(scenes)} < 6")
        
        # 检查每个场景
        for scene in scenes:
            scene_id = scene.get("scene_id", "?")
            
            if not scene.get("narration"):
                score -= 0.1
                issues.append(f"场景{scene_id}缺少narration")
            
            if not scene.get("key_elements"):
                score -= 0.1
                issues.append(f"场景{scene_id}缺少key_elements")
            
            if not scene.get("visual_type"):
                score -= 0.05
                issues.append(f"场景{scene_id}缺少visual_type")
        
        return max(0, score), issues
    
    def check_html_quality(self, html_content, scene_id=None):
        """检查HTML质量"""
        score = 1.0
        issues = []
        
        if not html_content:
            return 0, ["HTML内容为空"]
        
        # 检查长度
        if len(html_content) < 3000:
            score -= 0.3
            issues.append(f"HTML过短: {len(html_content)} < 3000")
        
        # 检查CSS opacity:0
        css_opacity_count = len(re.findall(r'style="[^"]*opacity:\s*0', html_content))
        if css_opacity_count > 0:
            score -= 0.5
            issues.append(f"CSS opacity:0存在: {css_opacity_count}个")
        
        # 检查是否有可见内容
        text_elements = re.findall(r'font-size:\s*\d+px[^"]*"[^>]*>[^<]{3,}', html_content)
        if len(text_elements) < 3:
            score -= 0.3
            issues.append(f"可见内容不足: {len(text_elements)} < 3")
        
        # 检查背景色
        if "#1a1a2e" not in html_content and "background" not in html_content[:500]:
            score -= 0.2
            issues.append("缺少深色背景")
        
        # 检查GSAP
        if "gsap" not in html_content.lower():
            score -= 0.2
            issues.append("缺少GSAP动画")
        
        return max(0, score), issues
    
    def check_video_quality(self, video_path):
        """检查视频质量"""
        score = 1.0
        issues = []
        
        if not os.path.exists(video_path):
            return 0, ["视频文件不存在"]
        
        # 检查文件大小
        size = os.path.getsize(video_path)
        if size < 100000:
            score -= 0.5
            issues.append(f"视频文件过小: {size} bytes")
        
        # 检查时长和分辨率
        try:
            import subprocess
            result = subprocess.run(
                f'ffprobe -v quiet -show_entries format=duration,size -show_entries stream=width,height -of json "{video_path}"',
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data["format"]["duration"])
                width = data["streams"][0]["width"]
                height = data["streams"][0]["height"]
                
                if duration < 60:
                    score -= 0.2
                    issues.append(f"视频时长过短: {duration}s < 60s")
                
                if width < 1920 or height < 1080:
                    score -= 0.2
                    issues.append(f"分辨率不足: {width}x{height} < 1920x1080")
        except Exception as e:
            self.log(f"检查视频质量失败: {e}", "WARN")
        
        return max(0, score), issues
    
    def trace_failure(self, pipeline_result):
        """追溯失败根因"""
        self.log("=" * 50)
        self.log("开始质量追溯")
        self.log("=" * 50)
        
        all_issues = []
        
        # 检查每个环节
        checkpoints = {
            "topic_selected": self.check_topic_quality,
            "script_data": self.check_script_quality,
            "storyboard": self.check_storyboard_quality,
        }
        
        for key, check_func in checkpoints.items():
            data = pipeline_result.get(key)
            if data:
                score, issues = check_func(data)
                if issues:
                    all_issues.append({
                        "skill": key,
                        "score": score,
                        "issues": issues
                    })
                    self.log(f"❌ {key}: {issues}", "WARN")
                else:
                    self.log(f"✅ {key}: 通过")
        
        # 检查文件
        file_checks = {
            "voice_path": self.check_voice_quality,
            "bgm_path": self.check_bgm_quality,
            "video_path": self.check_video_quality,
        }
        
        for key, check_func in file_checks.items():
            path = pipeline_result.get(key)
            if path:
                score, issues = check_func(path)
                if issues:
                    all_issues.append({
                        "skill": key,
                        "score": score,
                        "issues": issues
                    })
                    self.log(f"❌ {key}: {issues}", "WARN")
                else:
                    self.log(f"✅ {key}: 通过")
        
        # 检查HTML场景
        compositions_dir = Path(pipeline_result.get("project_root", ".")) / "hf_render_project" / "compositions"
        if compositions_dir.exists():
            for html_file in sorted(compositions_dir.glob("beat-*.html")):
                if html_file.name == "beat-outro.html":
                    continue
                html_content = html_file.read_text(encoding="utf-8")
                scene_id = html_file.stem
                score, issues = self.check_html_quality(html_content, scene_id)
                if issues:
                    all_issues.append({
                        "skill": "hf_builder",
                        "scene": scene_id,
                        "score": score,
                        "issues": issues
                    })
                    self.log(f"❌ {scene_id}: {issues}", "WARN")
                else:
                    self.log(f"✅ {scene_id}: 通过")
        
        # 保存报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "issues": all_issues,
            "summary": {
                "total_issues": len(all_issues),
                "critical": len([i for i in all_issues if i["score"] < 0.5]),
                "warning": len([i for i in all_issues if 0.5 <= i["score"] < 0.8])
            }
        }
        
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log("=" * 50)
        self.log(f"追溯完成: {report['summary']}")
        self.log("=" * 50)
        
        return report


# 全局实例
_tracker = None

def get_tracker():
    global _tracker
    if _tracker is None:
        _tracker = QualityTracker()
    return _tracker

def check_skill_quality(skill_name, data):
    tracker = get_tracker()
    check_func = getattr(tracker, f"check_{skill_name}_quality", None)
    if check_func:
        return check_func(data)
    return 1.0, []

def trace_failure(pipeline_result):
    return get_tracker().trace_failure(pipeline_result)


if __name__ == "__main__":
    # 测试
    tracker = QualityTracker()
    
    # 测试脚本质量检查
    test_script = {
        "voiceover_sections": [
            {"content": "你绝对想不到，这个话题有多火"},
            {"content": "说白了，这就是一个机会"},
            {"content": "你品，细品这个数据"},
            {"content": "真相是，市场在变化"},
            {"content": "别被忽悠了，要看本质"},
            {"content": "记住，行动才是关键"}
        ]
    }
    
    score, issues = tracker.check_script_quality(test_script)
    print(f"\n脚本质量: {score}")
    print(f"问题: {issues}")
