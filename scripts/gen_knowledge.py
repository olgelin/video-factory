#!/usr/bin/env python3
"""
gen_knowledge.py — 自动扫描代码库，生成知识库文档。

运行方式:
    cd video-factory
    python scripts/gen_knowledge.py

产出:
    knowledge/codebase/skills.md      — 每个 skill 的功能、输入输出
    knowledge/codebase/pipeline.md    — pipeline 步骤和数据流
    knowledge/codebase/tools.md       — 本地工具列表
    knowledge/tool-configs/*.md       — 每个工具的配置详情
"""
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
CODEBASE_DIR = KNOWLEDGE_DIR / "codebase"
SKILLS_DIR = PROJECT_ROOT / "hf-project" / "skills"
PIPELINE_DIR = PROJECT_ROOT / "pipeline_defs"
TOOLS_DIR = PROJECT_ROOT / "tools"

# ── 工具函数 ──

def scan_skills() -> list[dict]:
    """扫描所有 skill，提取元信息。"""
    skills = []
    if not SKILLS_DIR.exists():
        return skills
    
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        impl = skill_dir / "impl.py"
        skill_md = skill_dir / "SKILL.md"
        if not impl.exists():
            continue
        
        # 读 impl.py 找 run() 函数签名和关键逻辑
        code = impl.read_text(encoding="utf-8", errors="ignore")
        
        # 提取函数和关键调用
        functions = re.findall(r'^def (\w+)\(', code, re.MULTILINE)
        imports = re.findall(r'^(?:from|import)\s+(\S+)', code, re.MULTILINE)
        
        # 提取 print 日志了解步骤
        prints = re.findall(r'print\(f?"[^"]*\[(\w+)\][^"]*"', code)
        
        # 读 SKILL.md 获取描述
        desc = ""
        if skill_md.exists():
            front = skill_md.read_text(encoding="utf-8")
            m = re.search(r'description:\s*"([^"]+)"', front)
            if m:
                desc = m.group(1)
        
        skills.append({
            "name": skill_dir.name,
            "description": desc,
            "functions": functions[:15],
            "key_imports": imports[:10],
            "log_tags": list(set(prints))[:8],
            "lines": len(code.split('\n')),
            "has_skill_md": skill_md.exists(),
        })
    
    return skills


def scan_pipelines() -> list[dict]:
    """扫描所有 pipeline 定义。"""
    pipelines = []
    if not PIPELINE_DIR.exists():
        return pipelines
    
    for yaml_file in sorted(PIPELINE_DIR.glob("*.yaml")):
        content = yaml_file.read_text(encoding="utf-8")
        
        # 提取 steps
        steps = []
        for m in re.finditer(r'-\s+name:\s*(\S+).*?\n\s+step:\s*([\d.]+).*?\n\s+skill:\s*(\S+)', content, re.DOTALL):
            steps.append({
                "name": m.group(1),
                "step": m.group(2),
                "skill": m.group(3),
            })
        
        pipelines.append({
            "file": yaml_file.name,
            "name": re.search(r'name:\s*(\S+)', content).group(1) if 'name:' in content else "?",
            "description": re.search(r'description:\s*>\s*\n\s*(.*)', content).group(1) if 'description:' in content else "",
            "steps": steps,
        })
    
    return pipelines


def scan_tools() -> list[dict]:
    """扫描 tools/ 目录。"""
    tools = []
    if not TOOLS_DIR.exists():
        return tools
    
    for tool_dir in sorted(TOOLS_DIR.iterdir()):
        if not tool_dir.is_dir():
            continue
        cli = tool_dir / "cli.py"
        reqs = tool_dir / "requirements.txt"
        venv = tool_dir / ".venv"
        
        tools.append({
            "name": tool_dir.name,
            "has_cli": cli.exists(),
            "has_reqs": reqs.exists(),
            "has_venv": venv.exists(),
        })
    
    return tools


# ── 生成文档 ──

def gen_skills_doc(skills: list[dict]) -> str:
    """生成 skills.md"""
    lines = [
        f"# Skills 模块文档",
        f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"共 {len(skills)} 个 skill。",
        f"",
    ]
    
    for s in skills:
        name = s["name"]
        desc = s["description"] or "(无描述)"
        lines.append(f"## {name}")
        lines.append(f"")
        lines.append(f"**描述**: {desc}")
        lines.append(f"**代码行数**: {s['lines']}")
        if s["functions"]:
            lines.append(f"**主要函数**: {', '.join(s['functions'][:8])}")
        if s["log_tags"]:
            lines.append(f"**日志标签**: {', '.join(s['log_tags'][:6])}")
        lines.append(f"**SKILL.md**: {'✅' if s['has_skill_md'] else '❌ 缺失'}")
        lines.append(f"")
    
    return '\n'.join(lines)


def gen_pipeline_doc(pipelines: list[dict]) -> str:
    """生成 pipeline.md"""
    lines = [
        f"# Pipeline 文档",
        f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
    ]
    
    for p in pipelines:
        lines.append(f"## {p['name']} (`{p['file']}`)")
        lines.append(f"")
        if p["description"]:
            lines.append(f"{p['description']}")
            lines.append(f"")
        lines.append(f"| 步骤 | 名称 | Skill |")
        lines.append(f"|------|------|-------|")
        for s in p["steps"]:
            lines.append(f"| {s['step']} | {s['name']} | {s['skill']} |")
        lines.append(f"")
    
    return '\n'.join(lines)


def gen_tools_doc(tools: list[dict]) -> str:
    """生成 tools.md"""
    lines = [
        f"# 本地工具",
        f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
    ]
    
    for t in tools:
        lines.append(f"## {t['name']}")
        lines.append(f"- CLI: {'✅' if t['has_cli'] else '❌'}")
        lines.append(f"- 依赖文件: {'✅' if t['has_reqs'] else '❌'}")
        lines.append(f"- 独立 venv: {'✅' if t['has_venv'] else '❌'}")
        lines.append(f"")
    
    return '\n'.join(lines)


# ── 主入口 ──

def main():
    CODEBASE_DIR.mkdir(parents=True, exist_ok=True)
    
    print("🔍 扫描代码库...")
    
    skills = scan_skills()
    pipelines = scan_pipelines()
    tools = scan_tools()
    
    print(f"   Skills: {len(skills)}")
    print(f"   Pipelines: {len(pipelines)}")
    print(f"   Tools: {len(tools)}")
    
    # 生成文档
    (CODEBASE_DIR / "skills.md").write_text(gen_skills_doc(skills), encoding="utf-8")
    print(f"   ✅ knowledge/codebase/skills.md")
    
    (CODEBASE_DIR / "pipeline.md").write_text(gen_pipeline_doc(pipelines), encoding="utf-8")
    print(f"   ✅ knowledge/codebase/pipeline.md")
    
    (CODEBASE_DIR / "tools.md").write_text(gen_tools_doc(tools), encoding="utf-8")
    print(f"   ✅ knowledge/codebase/tools.md")
    
    # 也更新 SHARED 的 tool-configs
    shared_tools = Path(os.environ.get("HERMES_HOME", "")) / ".." / "workspace" / "xiaoshan" / "SHARED" / "knowledge" / "tool-configs"
    shared_tools = PROJECT_ROOT.parent / "SHARED" / "knowledge" / "tool-configs"
    if shared_tools.exists():
        for t in tools:
            cfg_file = shared_tools / f"{t['name']}.md"
            if not cfg_file.exists():
                cfg_file.write_text(
                    f"# {t['name']}\n\n"
                    f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"- CLI: {'✅' if t['has_cli'] else '❌'}\n"
                    f"- 独立 venv: {'✅' if t['has_venv'] else '❌'}\n\n"
                    f"## 已知问题\n\n(待补充)\n",
                    encoding="utf-8"
                )
        print(f"   ✅ SHARED/knowledge/tool-configs/ 已同步")
    
    print(f"\n✅ 知识库自动生成完成")


if __name__ == "__main__":
    main()
