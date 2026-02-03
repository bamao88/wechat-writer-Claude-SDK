# Phase 1: Foundation Setup - Context

**Gathered:** 2026-02-03 (Updated: 2026-02-03)
**Status:** Ready for planning

<domain>
## Phase Boundary

搭建CLI入口和NotebookLM工具集成基础。用户能够通过命令行启动写作流程,Agent能够调用NotebookLM搜索工具进行查询并获取结果。

**核心变化**: 使用 PleasePrompto/notebooklm-skill 替代 jacob-bd/notebooklm-mcp-cli

</domain>

<decisions>
## Implementation Decisions

### CLI接口设计
- **参数设计**: 单一必填位置参数(选题) — `python main.py "选题"`
- **参数验证**: 验证选题非空(拒绝空字符串或仅空格)
- **帮助命令**: 支持 `-h` / `--help` 显示用法示例
- **错误信息**: 使用中文错误信息,适配中文用户

### NotebookLM Skill调用方式
- **调用方式**: subprocess 调用 `scripts/ask_question.py`
- **必填参数**: `--question "查询内容"`
- **笔记本参数**: `--notebook-url "..."` (使用项目配置的 NOTEBOOK_URL)
- **可选参数**: `--show-browser` (调试用，默认 headless)
- **脚本路径**: 从环境变量 `NOTEBOOKLM_SKILL_PATH` 读取 Skill 目录位置
- **标准输出捕获**: 从 stdout 按分隔线解析答案正文
- **错误捕获**: 捕获 stderr 和 returncode，超时控制按配置的 `NOTEBOOKLM_TIMEOUT_SEC`

### 认证配置管理
- **认证实现**: 完全由 Skill 自己管理，项目不实现认证逻辑
- **认证状态**: Skill 维护在 `~/.claude/skills/notebooklm/data/` (auth_info.json、browser_state/)
- **认证检查**: 不主动检查认证状态，每次调用都直接执行
- **首次使用**: 未认证时 Skill 打印 "Not authenticated. Run: python auth_manager.py setup"，我们将此视为失败并把提示信息放入 error
- **认证失败处理**: 当做普通工具调用失败处理，返回 ToolResult(success=False, error=stderr内容)

### 工具接口适配
- **成功响应**: ToolResult(success=True, content=从stdout解析出的答案字符串)
- **失败响应**: ToolResult(success=False, content="", error=错误说明)
- **输出解析**: 从 Skill stdout 按分隔线提取答案正文
- **错误映射**: 超时、脚本exit≠0、找不到脚本路径都映射为统一的 ToolResult 错误形态
- **错误详情**: error 字段包含 stderr 内容或简短说明，方便排查

### 配置参数调整
- **保留配置**:
  - `NOTEBOOK_URL` — 传递给 --notebook-url
  - `NOTEBOOKLM_RETRY_COUNT=3` — 重试次数
  - `NOTEBOOKLM_RETRY_DELAY_SEC=2` — 重试间隔
  - `NOTEBOOKLM_TIMEOUT_SEC=120` — 超时时间
  - `LOG_LEVEL=INFO` — 日志级别
- **新增配置**:
  - `NOTEBOOKLM_SKILL_PATH` — Skill 目录路径(指向 notebooklm-skill 根目录)
- **移除配置**:
  - `NOTEBOOK_ID` — 不再需要(Skill 使用 notebook-url)

### 工具调用错误处理
- **调用失败重试**: 按 `.env` 配置的重试策略处理
  - 重试失败后将错误返回给 Agent(不退出)
  - 错误信息包含"已重试N次"和"最后一次错误:xxx"
- **超时控制**: 从 `.env` 读取 `NOTEBOOKLM_TIMEOUT_SEC=120`
- **脚本未找到**: 立即失败，提示检查 `NOTEBOOKLM_SKILL_PATH` 配置
- **网络错误**: 按重试策略处理

### CLI输出和日志
- **Console输出**: 简单文本进度提示,显示关键阶段如 `[开始检索]`、`[正在写作]`、`[完成]`
  - 无需额外依赖(不使用进度条或颜色库)
  - 目标:先跑通流程
- **日志系统**: 多级别日志 (DEBUG/INFO/WARNING/ERROR)
- **日志配置**: 从 `.env` 读取日志级别 (`LOG_LEVEL=INFO`)

### Claude's Discretion
- 日志输出位置(console only或console+文件)
- 具体的帮助文本内容和格式
- 错误信息的详细措辞
- stdout 分隔线解析的具体实现
- 重试逻辑的具体实现细节

</decisions>

<specifics>
## Specific Ideas

- **最小化依赖**: 简单文本输出,不引入colorama/tqdm等,优先验证流程可行性
- **配置中心化**: 所有外部配置(NotebookLM URL、Skill路径、重试参数、超时、日志级别)都通过 `.env` 管理
- **错误透明化**: 工具调用失败时,向Agent返回详细的错误上下文(重试次数、stderr内容),而非静默失败
- **使用 notebooklm-skill**: 集成 https://github.com/PleasePrompto/notebooklm-skill
- **认证解耦**: 认证完全由 Skill 管理，项目代码不涉及认证逻辑，降低复杂度

</specifics>

<deferred>
## Deferred Ideas

None — 讨论聚焦在 Phase 1 范围内。

</deferred>

---

*Phase: 01-foundation-setup*
*Context gathered: 2026-02-03*
*Updated: 2026-02-03 (切换到 notebooklm-skill)*
