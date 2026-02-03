# Requirements: AI 写作助手

**Defined:** 2026-02-03
**Core Value:** 能够调用 NotebookLM 搜索资料并完成端到端的文章生成流程，验证「研究 → 规划 → 写作」的完整闭环可行性。

## v1 Requirements

### CLI Interface

- [ ] **CLI-01**: 用户可以通过命令行传入选题参数启动写作流程

### NotebookLM Integration

- [ ] **NBK-01**: 系统可以将 NotebookLM MCP Tool 集成到 Claude SDK 中
- [ ] **NBK-02**: Agent 可以调用 NotebookLM Tool 搜索相关资料

### Research Phase

- [ ] **RSH-01**: Agent 可以基于选题搜索 NotebookLM 笔记本获取资料
- [ ] **RSH-02**: Agent 可以将搜索结果整理成调研报告

### Outline Generation

- [ ] **OTL-01**: Agent 可以基于调研结果生成文章大纲

### Article Writing

- [ ] **ART-01**: Agent 可以基于大纲生成完整文章内容

### Output Management

- [ ] **OUT-01**: 系统可以保存调研结果到文件
- [ ] **OUT-02**: 系统可以保存大纲到文件
- [ ] **OUT-03**: 系统可以保存最终文章到文件

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Multi-Model Support

- **MLM-01**: 通过 LiteLLM 支持 OpenAI API
- **MLM-02**: 通过 LiteLLM 支持 Minimax API
- **MLM-03**: 用户可以配置使用不同的 AI 模型

### Multi-Agent Architecture

- **MAG-01**: 实现研究员 Agent 专门负责资料搜索
- **MAG-02**: 实现写作 Agent 专门负责内容生成
- **MAG-03**: 实现 Agent 间的协调和数据传递

### CLI Enhancement

- **CLE-01**: 支持 --output 参数指定输出目录
- **CLE-02**: 支持 --model 参数指定 AI 模型
- **CLE-03**: 支持 --notebook-id 参数指定 NotebookLM 笔记本
- **CLE-04**: 支持交互式模式逐步引导用户

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| API 服务接口 | v1 仅需 CLI 工具，服务化延后 |
| 实时网页抓取 | v1 聚焦 NotebookLM 笔记本，避免复杂度 |
| 本地文档搜索 | v1 仅使用已有 NotebookLM 笔记本 |
| Python SDK 封装 | v1 聚焦验证流程，不做库封装 |
| 用户认证系统 | 个人工具，无需认证 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 1 | Pending |
| NBK-01 | Phase 1 | Pending |
| NBK-02 | Phase 1 | Pending |
| RSH-01 | Phase 2 | Pending |
| RSH-02 | Phase 2 | Pending |
| OTL-01 | Phase 2 | Pending |
| ART-01 | Phase 2 | Pending |
| OUT-01 | Phase 3 | Pending |
| OUT-02 | Phase 3 | Pending |
| OUT-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-03*
*Last updated: 2026-02-03 after roadmap creation*
