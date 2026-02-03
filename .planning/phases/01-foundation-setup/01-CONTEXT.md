# Phase 1: Foundation Setup - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

搭建CLI入口和NotebookLM工具集成基础。用户能够通过命令行启动写作流程,Agent能够调用NotebookLM MCP工具进行搜索并获取结果。

</domain>

<decisions>
## Implementation Decisions

### CLI接口设计
- **参数设计**: 单一必填位置参数(选题) — `python main.py "选题"`
- **参数验证**: 验证选题非空(拒绝空字符串或仅空格)
- **帮助命令**: 支持 `-h` / `--help` 显示用法示例
- **错误信息**: 使用中文错误信息,适配中文用户

### NotebookLM工具集成方式
- **集成方式**: 将NotebookLM MCP工具包装为Claude Tool接口(标准化接口)
- **工具发现**: 硬编码工具定义,不需要动态发现机制
- **MCP配置管理**: 从`.env`文件读取连接配置(不硬编码)
  - 已有配置: `NOTEBOOK_URL`, `NOTEBOOK_ID`
  - MCP连接配置也放在`.env`
- **返回格式**: 直接返回原始JSON/文本结果,由Agent自行解析

### 工具调用错误处理
- **调用失败重试**: 按`.env`配置的重试策略处理
  - `NOTEBOOKLM_RETRY_COUNT=3` (重试次数)
  - `NOTEBOOKLM_RETRY_DELAY_SEC=2` (重试间隔)
  - 重试失败后将错误返回给Agent(不退出),错误信息包含"已重试N次"和"最后一次错误:xxx"
- **超时控制**: 支持超时设置,从`.env`读取 `NOTEBOOKLM_TIMEOUT_SEC=120`
- **认证错误**: 认证失败时立即退出,提示检查`.env`配置
- **网络错误**: 按重试策略处理(与调用失败相同)

### CLI输出和日志
- **Console输出**: 简单文本进度提示,显示关键阶段如 `[开始检索]`、`[正在写作]`、`[完成]`
  - 无需额外依赖(不使用进度条或颜色库)
  - 目标:先跑通流程
- **日志系统**: 多级别日志 (DEBUG/INFO/WARNING/ERROR)
- **日志配置**: 从`.env`读取日志级别 (`LOG_LEVEL=INFO`)

### Claude's Discretion
- 日志输出位置(console only或console+文件)
- 具体的帮助文本内容和格式
- 错误信息的详细措辞
- 工具包装的具体实现方式
- 重试逻辑的具体实现细节

</decisions>

<specifics>
## Specific Ideas

- **最小化依赖**: 简单文本输出,不引入colorama/tqdm等,优先验证流程可行性
- **配置中心化**: 所有外部配置(NotebookLM URL/ID、重试参数、超时、日志级别)都通过`.env`管理
- **错误透明化**: 工具调用失败时,向Agent返回详细的错误上下文(重试次数、最后错误),而非静默失败
- **使用notebooklm-mcp-cli**: 集成 https://github.com/jacob-bd/notebooklm-mcp-cli

</specifics>

<deferred>
## Deferred Ideas

None — 讨论聚焦在Phase 1范围内。

</deferred>

---

*Phase: 01-foundation-setup*
*Context gathered: 2026-02-03*
