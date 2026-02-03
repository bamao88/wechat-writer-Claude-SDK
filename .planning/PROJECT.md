# AI 写作助手

## What This Is

一个基于 Claude SDK 的 Python CLI 写作助手，帮助用户通过「选题调研 → 列大纲 → 写文章」的流程生成文章。通过 NotebookLM MCP Tool 搜索已有笔记本资料，输出包含调研结果、大纲和最终文章的完整写作过程。个人工具，命令行调用。

## Core Value

能够调用 NotebookLM 搜索资料并完成端到端的文章生成流程，验证「研究 → 规划 → 写作」的完整闭环可行性。

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] CLI 能够接收选题参数并启动写作流程
- [ ] Agent 能够调用 NotebookLM MCP Tool 搜索相关资料
- [ ] Agent 能够基于调研结果生成文章大纲
- [ ] Agent 能够基于大纲生成完整文章内容
- [ ] 系统保存中间过程到文件（调研结果、大纲、最终文章）
- [ ] 使用 Claude SDK 原生 API 完成真实 API 闭环

### Out of Scope

- LiteLLM 多模型支持 — v2 功能，v1 聚焦 Claude 原生 API 验证
- 多 Agent 架构（研究员/写作者分离）— v1 用单 Agent 验证流程可行性
- 复杂 CLI 参数（--output、--model 等）— v1 保持最简调用方式
- API 服务或 SDK 封装 — v1 仅需 CLI 工具
- 网页抓取或本地文档搜索 — v1 仅使用已有的 NotebookLM 笔记本

## Context

**现有资源：**
- notebooklm-mcp-cli 已验证可用
- .env 中已有部分配置（NotebookLM 相关）
- 资料来源为用户已创建的 NotebookLM 笔记本

**使用场景：**
- 文章类型：综合类型（技术博客、行业分析、知识总结等）
- 用户：个人使用，命令行工具
- 调用方式：`python main.py "选题"`

**架构演进路径：**
- v1：单 Agent + Claude 原生 API（快速验证原型）
- v2：引入 LiteLLM 支持 OpenAI、Minimax 等多模型
- v3：多 Agent 架构优化（研究员 Agent + 写作 Agent）

## Constraints

- **Tech stack**: Python — 现有技术栈
- **API Provider**: v1 仅支持 Claude 原生 API（Anthropic SDK）— 聚焦快速验证
- **Tool Integration**: NotebookLM 通过 MCP (notebooklm-mcp-cli) 集成 — 已验证方案
- **Architecture**: v1 单 Agent 架构 — 保持简单，验证流程
- **Interface**: 简单 CLI 脚本 — 最小可用接口

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 使用 Claude 原生 SDK（非 LiteLLM） | v1 聚焦快速验证 API 闭环，避免多层抽象复杂度 | — Pending |
| NotebookLM 通过 MCP 包装成 Claude Tool | 标准化接口，利用 Claude SDK 的 tool use 能力 | — Pending |
| 单 Agent 架构 | 验证完整流程可行性，为后续多 Agent 优化打基础 | — Pending |
| 保存中间过程到文件 | 便于调试和观察 Agent 推理过程 | — Pending |

---
*Last updated: 2026-02-03 after initialization*
