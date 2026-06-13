"""
quality_gate/skill.py — 质检（HyperFrames Step 6: Quality Check）
功能：用HyperFrames官方工具检查HTML composition的质量
输出：qa_report.json

使用官方工具：
- npx hyperframes lint — HTML规范检查
- npx hyperframes validate — WCAG对比度检查
- npx hyperframes inspect — 视觉布局检查
- animation-map — 动画编排检查
"""

import os
import json
import subprocess
from pathlib import Path

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
HF_PROJECT_DIR = Path(__file__).parent.parent.parent
QA_REPORT_PATH = OUTPUT_DIR / "qa_report.json"


def run_command(cmd: str, cwd: str = None, timeout: int = 120) -> tuple:
    """运行命令，返回(returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def run_lint(project_dir: str) -> dict:
    """运行hyperframes lint"""
    print("  [quality-gate] Running lint...")
    returncode, stdout, stderr = run_command(
        "npx hyperframes lint", cwd=project_dir, timeout=60
    )

    result = {
        "tool": "lint",
        "passed": returncode == 0,
        "output": stdout,
        "errors": stderr,
    }

    if returncode == 0:
        print("  [quality-gate] lint: ✅ PASS")
    else:
        print(f"  [quality-gate] lint: ❌ FAIL")
        if stdout:
            print(f"    {stdout[:200]}")
        if stderr:
            print(f"    {stderr[:200]}")

    return result


def run_validate(project_dir: str) -> dict:
    """运行hyperframes validate（WCAG对比度检查）"""
    print("  [quality-gate] Running validate...")
    returncode, stdout, stderr = run_command(
        "npx hyperframes validate", cwd=project_dir, timeout=120
    )

    result = {
        "tool": "validate",
        "passed": returncode == 0,
        "output": stdout,
        "errors": stderr,
    }

    if returncode == 0:
        print("  [quality-gate] validate: ✅ PASS")
    else:
        print(f"  [quality-gate] validate: ⚠️ WARNINGS")
        if stdout:
            # 提取警告信息
            lines = stdout.split("\n")
            warnings = [l for l in lines if "⚠" in l or "warning" in l.lower()]
            for w in warnings[:5]:
                print(f"    {w}")

    return result


def run_inspect(project_dir: str) -> dict:
    """运行hyperframes inspect（视觉布局检查）"""
    print("  [quality-gate] Running inspect...")
    returncode, stdout, stderr = run_command(
        "npx hyperframes inspect --samples 10", cwd=project_dir, timeout=180
    )

    result = {
        "tool": "inspect",
        "passed": returncode == 0,
        "output": stdout,
        "errors": stderr,
    }

    if returncode == 0:
        print("  [quality-gate] inspect: ✅ PASS")
    else:
        print(f"  [quality-gate] inspect: ⚠️ ISSUES FOUND")
        if stdout:
            lines = stdout.split("\n")
            issues = [l for l in lines if "overflow" in l.lower() or "clip" in l.lower()]
            for issue in issues[:5]:
                print(f"    {issue}")

    return result


def run_custom_checks(project_dir: str) -> dict:
    """运行自定义检查（补充官方工具不覆盖的）"""
    print("  [quality-gate] Running custom checks...")

    issues = []
    index_path = Path(project_dir) / "index.html"

    if not index_path.exists():
        issues.append("index.html不存在")
        return {"tool": "custom", "passed": False, "issues": issues}

    content = index_path.read_text(encoding="utf-8")

    # 检查1：data-width/data-height
    if 'data-width="1920"' not in content:
        issues.append("缺少data-width=\"1920\"")
    if 'data-height="1080"' not in content:
        issues.append("缺少data-height=\"1080\"")

    # 检查2：data-composition-id
    if 'data-composition-id' not in content:
        issues.append("缺少data-composition-id")

    # 检查3：GSAP引用
    if "gsap" not in content.lower():
        issues.append("缺少GSAP引用")

    # 检查4：场景数量
    scene_count = content.count("data-composition-src")
    if scene_count == 0:
        # 检查是否有内联场景
        scene_count = content.count("data-composition-id") - 1  # 减去root
    if scene_count < 3:
        issues.append(f"场景数量过少: {scene_count}")

    # 检查5：音频引用
    has_audio = "<audio" in content
    if not has_audio:
        issues.append("缺少音频引用（<audio>标签）")

    # 检查6：中文字符在CSS注释中
    import re
    css_comments = re.findall(r'/\*.*?\*/', content, re.DOTALL)
    for comment in css_comments:
        if re.search(r'[\u4e00-\u9fff]', comment):
            issues.append(f"CSS注释中包含非ASCII字符: {comment[:50]}...")
            break

    passed = len(issues) == 0
    if passed:
        print("  [quality-gate] custom checks: ✅ PASS")
    else:
        print(f"  [quality-gate] custom checks: ⚠️ {len(issues)} issues")
        for issue in issues:
            print(f"    - {issue}")

    return {
        "tool": "custom",
        "passed": passed,
        "issues": issues,
    }


def run(context: dict) -> dict:
    """主入口：运行质检"""

    topic = context.get("topic", "未知话题")
    print(f"  [quality-gate] 为 '{topic}' 运行质检...")

    # 获取项目目录
    project_dir = context.get("hf_project_dir") or str(HF_PROJECT_DIR / "hf_render_project")
    if not os.path.exists(project_dir):
        print(f"  ❌ [quality-gate] 项目目录不存在: {project_dir}")
        return context

    # 运行各项检查
    results = {
        "topic": topic,
        "project_dir": project_dir,
        "checks": {},
        "overall_passed": True,
        "issues_count": 0,
    }

    # 1. Lint
    lint_result = run_lint(project_dir)
    results["checks"]["lint"] = lint_result
    if not lint_result["passed"]:
        results["overall_passed"] = False
        results["issues_count"] += 1

    # 2. Validate
    validate_result = run_validate(project_dir)
    results["checks"]["validate"] = validate_result
    if not validate_result["passed"]:
        results["issues_count"] += 1
        # validate警告不算失败，只记录

    # 3. Inspect
    inspect_result = run_inspect(project_dir)
    results["checks"]["inspect"] = inspect_result
    if not inspect_result["passed"]:
        results["issues_count"] += 1
        # inspect问题不算失败，只记录

    # 4. Custom checks
    custom_result = run_custom_checks(project_dir)
    results["checks"]["custom"] = custom_result
    if not custom_result["passed"]:
        results["overall_passed"] = False
        results["issues_count"] += len(custom_result.get("issues", []))

    # 保存报告
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(QA_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  [quality-gate] 报告已保存: {QA_REPORT_PATH}")

    # 输出总结
    if results["overall_passed"]:
        print(f"  [quality-gate] ✅ 质检通过（{results['issues_count']}个警告）")
    else:
        print(f"  [quality-gate] ❌ 质检不通过（{results['issues_count']}个问题）")

    # 更新context
    context["qa_report_path"] = str(QA_REPORT_PATH)
    context["qa_passed"] = results["overall_passed"]
    context["qa_issues_count"] = results["issues_count"]

    return context


if __name__ == "__main__":
    # 测试
    test_context = {
        "topic": "2026高考第一批显眼包出现了",
        "hf_project_dir": "E:/Hermes-Agent/workspace/xiaoshan/video-factory/hf-project/hf_render_project",
    }
    result = run(test_context)
    print(f"\n✅ 测试完成")
    print(f"  通过: {result.get('qa_passed')}")
    print(f"  问题数: {result.get('qa_issues_count')}")
