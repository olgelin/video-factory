# 知识库

> 自动生成 + 人工维护。Agent 干活前先读这里。

## 结构

```
knowledge/
├── README.md              ← 这个文件
├── codebase/              ← 🤖 自动生成（扫描代码结构）
│   ├── skills.md          ←    每个 skill 干什么、输入输出
│   ├── pipeline.md        ←    pipeline 步骤和数据流
│   └── tools.md           ←    本地工具配置
├── constraints/           ← ✍️ 人工维护（违反就出 bug）
├── bug-patterns/          ← ✍️ 人工维护（缺陷 → 根因 → 修复链）
├── prompt-rules/          ← ✍️ 人工维护（LLM 提示词禁忌）
├── tool-configs/          ← ✍️+🤖（工具配置 + 已知坑）
└── design-decisions/      ← ✍️ 人工维护（设计决策和理由）
```

## 更新机制

- **自动更新**: 代码变更后跑 `python scripts/gen_knowledge.py` → 刷新 codebase/ 和 tool-configs/
- **手动更新**: 出 bug 后反推根因 → 写入 bug-patterns/ 和 constraints/

## 使用方式

Agent 启动时自动加载 AGENTS.md → 引导读取 knowledge/
