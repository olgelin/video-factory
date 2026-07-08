# 知识库

> 全公司共享的项目经验。踩过的坑，不会再踩第二遍。

## 结构

```
knowledge/
├── constraints/       ← 硬性约束（违反就出 bug）
├── bug-patterns/      ← 缺陷 → 根因 → 修复链
├── prompt-rules/      ← LLM 提示词设计禁忌
├── tool-configs/      ← 本地工具配置 + 已知坑
└── design-decisions/  ← 重要设计决策及理由
```

## 使用方式

- **AI agent**：干活前先读相关文件，避开已知坑
- **人类**：打开 Markdown 直接看
- **新项目**：从 `_template/knowledge/` 复制脚手架

## 跨项目共享

`SHARED/knowledge/` 里的东西所有项目通用。
改了 SHARED → 所有项目自动受益。
