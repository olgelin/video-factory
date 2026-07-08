# AGENTS.md

> Hermes Agent 工作指引。每次干活前自动加载。

## 启动时必读

1. **先读知识库**: `knowledge/README.md` — 了解项目约束和已知坑
2. **检查约束**: `knowledge/constraints/` — 当前 pipeline 的硬性规则
3. **查 bug 库**: `knowledge/bug-patterns/` — 这次的问题之前踩过没？
4. **看代码结构**: `knowledge/codebase/` — 自动生成的模块文档

## 出 bug 时

修复完代码后，**必须**把根因和修复链写入 `knowledge/bug-patterns/`，格式参考已有文件。

## 加新功能时

先检查 `knowledge/constraints/` 和 `knowledge/design-decisions/`，确认不会违反已有设计。

## 更新知识库

代码有结构性变更后，运行:
```bash
python scripts/gen_knowledge.py
```
