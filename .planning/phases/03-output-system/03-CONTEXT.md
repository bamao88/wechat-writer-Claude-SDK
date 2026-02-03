# Phase 3: Output System - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

捕获完整的工作流执行轨迹(thought trace)和最终文章输出,并持久化到文件系统。这个阶段负责通过SDK Hook实时记录agent的所有输出、工具调用和返回结果,并在任务完成时提取最终文章。

</domain>

<decisions>
## Implementation Decisions

### 输出目录时机和错误处理
- **创建时机**: CLI初始化时立即创建输出目录,在任何agent工作之前
- **目录命名格式**: `YYYY-MM-DD_HHMMSS_topic-slug` (例: `2026-02-03_143052_chan-pin-jing-li`)
- **Topic slug生成**: 中文转拼音,小写,连字符分隔 (例: "产品经理" → "chan-pin-jing-li")
- **创建失败处理**: Fail fast and exit — 无法创建输出目录时立即报错退出
- **目录位置**: `output/` 目录下

### article.md提取触发策略
- **触发时机**: End-of-conversation detection — 等待SDK会话完成信号(消息流自然结束)
- **多消息处理**: Final message only — 只使用最后一条assistant消息作为文章内容
- **内容验证**: No validation, trust output — 不验证文章结构,直接写入最后消息的内容

### thought_trace.md结构和格式
- **条目格式**: `## [序号] [时间戳] 类型` (例: `## [001] [14:30:52] Agent Output`)
- **内容区分**:
  - Agent文本输出: 使用blockquote (Markdown引用块)
  - 工具调用: 使用code block,包含工具名称和关键参数
  - 工具返回: 使用`<details>`折叠区域
- **工具调用细节**: Tool name + key params only — 只记录工具名称和关键参数(如search的query),省略冗长参数
- **工具返回长度**: Truncate with expand option — 长结果截取前500字符可见,其余放入折叠details区域

### 写入失败和可靠性处理
- **thought_trace.md写入失败**: 重试3次 → 失败后降级为内存缓冲 → 最后尝试一次性写入
- **写入策略**: 实时写入,每次追加 — 每有新内容立即追加到文件,最大化实时性
- **article.md写入失败**: 重试3次 → 失败后软失败(记录错误但不中止,至少trace保留了)
- **文件锁定**: 不使用锁(单进程假设) — 假设单进程顺序写入,不加文件锁

### Claude's Discretion
- Markdown具体样式细节(间距、字体等)
- 序号和时间戳的具体格式细节
- 重试间隔时长
- 内存缓冲区大小
- 错误日志的具体格式

</decisions>

<specifics>
## Specific Ideas

- **黑匣子概念**: thought_trace.md就像飞机黑匣子,完整记录"检索 → 调整 → 再检索 → 写作"的全过程
- **无标记依赖**: 不要求模型输出【第一轮检索结果】等标记,解析和拆分完全由Hook和代码完成
- **Hook要求**: 能拦截SDK的每一次assistant输出(含流式)以及每一次tool_use/tool_result
- **可读性优先**: Markdown格式化便于阅读和调试

</specifics>

<deferred>
## Deferred Ideas

None — 讨论聚焦在Phase 3范围内。

</deferred>

---

*Phase: 03-output-system*
*Context gathered: 2026-02-03*
