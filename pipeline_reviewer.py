#!/usr/bin/env python3
"""
pipeline_reviewer.py - 视频质量自动诊断 + 反哺机制
Pipeline完成后自动运行，分析场景HTML，发现问题，生成修复建议

用法:
  python pipeline_reviewer.py                    # 分析当前pipeline输出
  python pipeline_reviewer.py --auto-fix         # 分析+自动修正skill
  python pipeline_reviewer.py --output-dir DIR   # 指定输出目录
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

# ============================================================
# 最佳实践规则库（不是模板，是质量标准）
# ============================================================

BEST_PRACTICES = {
    "gsap_animation_count": {
        "name": "GSAP动画数量",
        "threshold": 5,
        "check": lambda html: len(re.findall(r'(?:gsap|tl)\.(to|from|fromTo|timeline)', html)),
        "severity": "critical",
        "fix_hint": "增加更多gsap.from()入场动画，每个元素都要有入场效果",
    },
    "decoration_layers": {
        "name": "装饰层数量",
        "threshold": 3,
        "check": lambda html: sum([
            1 if "grid" in html.lower() or "linear-gradient" in html else 0,
            1 if "radial-gradient" in html else 0,
            1 if "ghost" in html.lower() or "opacity:0.0" in html or "opacity: 0.0" in html else 0,
            1 if "scan" in html.lower() or "scanline" in html.lower() else 0,
        ]),
        "severity": "warning",
        "fix_hint": "每个场景必须有grid网格+径向光晕+ghost text水印",
    },
    "data_visualization": {
        "name": "数据可视化",
        "threshold": 1,
        "check": lambda html: sum([
            1 if "countUp" in html or "textContent" in html else 0,
            1 if re.search(r'font-size:\s*(?:8[0-9]|9\d|1[0-4]\d)px', html) else 0,
            1 if "progress" in html.lower() or "scaleX" in html else 0,
        ]),
        "severity": "warning",
        "fix_hint": "有数字的场景必须有countUp动画+大字号数据卡片",
    },
    "three_layer_structure": {
        "name": "三层视觉结构",
        "threshold": 2,
        "check": lambda html: sum([
            1 if "z-index:0" in html or "z-index: 0" in html else 0,
            1 if re.search(r'z-index:\s*[12]', html) else 0,
            1 if re.search(r'z-index:\s*[3-9]', html) else 0,
        ]),
        "severity": "warning",
        "fix_hint": "必须有背景层(z:0)+内容层(z:1-2)+装饰层(z:3+)",
    },
    "color_saturation": {
        "name": "色彩饱和度",
        "threshold": 2,
        "check": lambda html: len(re.findall(r'#[0-9a-fA-F]{6}', html)),
        "severity": "info",
        "fix_hint": "至少2种不同颜色，核心数据用高亮色",
    },
    "glass_morphism": {
        "name": "玻璃态效果",
        "threshold": 1,
        "check": lambda html: 1 if "backdrop-filter" in html else 0,
        "severity": "info",
        "fix_hint": "数据卡片必须有backdrop-filter:blur玻璃态",
    },
    "text_glow": {
        "name": "文字发光",
        "threshold": 1,
        "check": lambda html: len(re.findall(r'text-shadow', html)),
        "severity": "info",
        "fix_hint": "标题必须有text-shadow发光效果",
    },
    "breathing_animation": {
        "name": "呼吸动画",
        "threshold": 1,
        "check": lambda html: len(re.findall(r'repeat:\s*-1', html)),
        "severity": "info",
        "fix_hint": "至少2个元素有repeat:-1呼吸动画",
    },
    "number_impact": {
        "name": "数字冲击效果",
        "threshold": 1,
        "check": lambda html: 1 if any(float(m) >= 1.5 for m in re.findall(r'scale:\s*([\d.]+)', html)) else 0,
        "severity": "warning",
        "fix_hint": "核心数字必须有scale放大→缩小的冲击效果",
    },
    "opacity_violation": {
        "name": "opacity:0违规",
        "threshold": 0,
        "check": lambda html: len(re.findall(r'style="[^"]*opacity:\s*0(?=[";\s])', html)),
        "severity": "critical",
        "invert": True,  # 0是好，>0是坏
        "fix_hint": "CSS中禁止opacity:0，用GSAP的from({opacity:0})代替",
    },
}


def analyze_scene(html_path: str) -> dict:
    """分析单个场景HTML，返回诊断结果"""
    html = Path(html_path).read_text(encoding="utf-8")
    results = {}
    
    for key, rule in BEST_PRACTICES.items():
        count = rule["check"](html)
        threshold = rule["threshold"]
        invert = rule.get("invert", False)
        
        if invert:
            passed = count <= threshold
        else:
            passed = count >= threshold
        
        results[key] = {
            "name": rule["name"],
            "value": count,
            "threshold": threshold,
            "passed": passed,
            "severity": rule["severity"],
            "fix_hint": rule["fix_hint"] if not passed else None,
        }
    
    return results


def analyze_all_scenes(compositions_dir: str) -> dict:
    """分析所有场景，生成诊断报告"""
    compositions = Path(compositions_dir)
    if not compositions.exists():
        return {"error": f"目录不存在: {compositions_dir}"}
    
    all_results = {}
    total_issues = {"critical": 0, "warning": 0, "info": 0}
    scene_summaries = []
    
    for html_file in sorted(compositions.glob("beat-*.html")):
        if html_file.name == "beat-outro.html":
            continue
        
        scene_id = html_file.stem  # e.g., "beat-1"
        results = analyze_scene(str(html_file))
        all_results[scene_id] = results
        
        # 统计问题
        scene_issues = []
        for key, r in results.items():
            if not r["passed"]:
                scene_issues.append({
                    "rule": key,
                    "name": r["name"],
                    "value": r["value"],
                    "threshold": r["threshold"],
                    "severity": r["severity"],
                    "fix_hint": r["fix_hint"],
                })
                total_issues[r["severity"]] += 1
        
        scene_summaries.append({
            "scene": scene_id,
            "total_rules": len(results),
            "passed": sum(1 for r in results.values() if r["passed"]),
            "failed": sum(1 for r in results.values() if not r["passed"]),
            "issues": scene_issues,
        })
    
    return {
        "analyzed_at": datetime.now().isoformat(),
        "total_scenes": len(scene_summaries),
        "total_issues": total_issues,
        "scenes": scene_summaries,
        "details": all_results,
    }


def generate_fix_instructions(report: dict) -> list:
    """根据诊断报告生成修复指令"""
    fixes = []
    
    # 收集所有失败的规则
    failed_rules = {}
    for scene in report.get("scenes", []):
        for issue in scene.get("issues", []):
            rule = issue["rule"]
            if rule not in failed_rules:
                failed_rules[rule] = {
                    "count": 0,
                    "scenes": [],
                    "fix_hint": issue["fix_hint"],
                    "severity": issue["severity"],
                }
            failed_rules[rule]["count"] += 1
            failed_rules[rule]["scenes"].append(scene["scene"])
    
    # 按严重程度排序
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    sorted_rules = sorted(
        failed_rules.items(),
        key=lambda x: severity_order.get(x[1]["severity"], 3)
    )
    
    for rule_name, info in sorted_rules:
        fixes.append({
            "rule": rule_name,
            "severity": info["severity"],
            "affected_scenes": info["scenes"],
            "affected_count": info["count"],
            "fix_hint": info["fix_hint"],
        })
    
    return fixes


def print_report(report: dict):
    """打印诊断报告"""
    print(f"\n{'='*60}")
    print(f"🔍 Pipeline质量诊断报告")
    print(f"{'='*60}")
    print(f"分析时间: {report['analyzed_at']}")
    print(f"场景总数: {report['total_scenes']}")
    issues = report['total_issues']
    print(f"问题统计: 🔴 {issues['critical']} 严重 | 🟡 {issues['warning']} 警告 | 🔵 {issues['info']} 提示")
    
    for scene in report.get("scenes", []):
        passed = scene["passed"]
        failed = scene["failed"]
        status = "✅" if failed == 0 else "⚠️"
        print(f"\n  {status} {scene['scene']}: {passed}/{scene['total_rules']} 通过")
        
        for issue in scene.get("issues", []):
            icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(issue["severity"], "⚪")
            print(f"    {icon} {issue['name']}: {issue['value']} (需要≥{issue['threshold']}) — {issue['fix_hint']}")
    
    # 生成修复建议
    fixes = generate_fix_instructions(report)
    if fixes:
        print(f"\n{'='*60}")
        print(f"🔧 修复建议（按优先级排序）")
        print(f"{'='*60}")
        for i, fix in enumerate(fixes, 1):
            icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(fix["severity"], "⚪")
            print(f"  {i}. {icon} [{fix['rule']}] 影响{fix['affected_count']}个场景")
            print(f"     修复: {fix['fix_hint']}")
            print(f"     场景: {', '.join(fix['affected_scenes'])}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline质量自动诊断")
    parser.add_argument("--output-dir", default=None, help="场景HTML目录")
    parser.add_argument("--auto-fix", action="store_true", help="自动修正skill")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    args = parser.parse_args()
    
    # 默认目录
    if args.output_dir:
        compositions_dir = args.output_dir
    else:
        base = Path(__file__).parent / "hf-project" / "hf_render_project" / "compositions"
        compositions_dir = str(base)
    
    # 分析
    report = analyze_all_scenes(compositions_dir)
    
    if "error" in report:
        print(f"❌ {report['error']}")
        sys.exit(1)
    
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    
    # 自动修正
    if args.auto_fix:
        fixes = generate_fix_instructions(report)
        critical_fixes = [f for f in fixes if f["severity"] == "critical"]
        if critical_fixes:
            print(f"\n⚠️ 发现{len(critical_fixes)}个严重问题，需要手动修复")
            for fix in critical_fixes:
                print(f"  - {fix['rule']}: {fix['fix_hint']}")
        else:
            print(f"\n✅ 无严重问题，所有场景质量达标")


if __name__ == "__main__":
    main()
