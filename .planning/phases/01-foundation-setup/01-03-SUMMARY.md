---
phase: 01-foundation-setup
plan: 03
subsystem: tools
tags: [notebooklm, mcp, subprocess, retry-logic, tdd, claude-sdk]

# Dependency graph
requires:
  - phase: 01-01
    provides: Config module with NotebookLM settings and retry configuration
provides:
  - NotebookLM tool wrapper with retry logic and timeout handling
  - ToolResult dataclass for success/error representation
  - NotebookLMTool class compatible with Claude SDK tool use API
affects: [01-04-integration, phase-2-agent-workflow]

# Tech tracking
tech-stack:
  added: [subprocess (stdlib), dataclasses (stdlib), typing (stdlib)]
  patterns: [TDD with RED-GREEN cycles, Tool wrapper pattern, Retry with exponential backoff]

key-files:
  created:
    - src/tools/__init__.py
    - src/tools/notebooklm.py
    - tests/unit/test_notebooklm_tool.py
    - tests/integration/__init__.py
  modified: []

key-decisions:
  - "Wrap nlm CLI (notebooklm-mcp-cli) as subprocess invocation"
  - "Return ToolResult to agent on failure (not crash) with detailed error messages"
  - "Retry logic respects config settings (retry_count, retry_delay_sec, timeout_sec)"
  - "Chinese error messages for user-facing failures"
  - "Tool schema compatible with Claude SDK messages API"

patterns-established:
  - "TDD pattern: Write failing tests (RED), implement to pass (GREEN), commit atomically"
  - "Tool wrapper pattern: search_notebook() function + NotebookLMTool class for SDK integration"
  - "Retry pattern: Configurable retry count with delay, detailed error after exhaustion"

# Metrics
duration: 2min
completed: 2026-02-03
---

# Phase 1 Plan 3: NotebookLM Tool Wrapper Summary

**TDD NotebookLM tool wrapper with retry logic, timeout handling, and Claude SDK integration using subprocess and comprehensive mocking**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-03T11:16:46Z
- **Completed:** 2026-02-03T11:19:09Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- NotebookLM search tool wrapper invokes `nlm notebook query <notebook_id> <query>` via subprocess
- Retry logic with configurable retry_count and retry_delay_sec from config
- Timeout handling via subprocess timeout parameter with graceful error handling
- Returns ToolResult to agent on failure (not crash) with detailed Chinese error messages
- NotebookLMTool class provides Claude SDK-compatible interface (name, description, input_schema)
- Full test coverage with 11 passing unit tests using mocks

## Task Commits

Each task was committed atomically following TDD methodology:

1. **Task 1: Create tools package structure** - `a515ecf` (chore)
2. **Task 2: TDD NotebookLM Tool - RED then GREEN**
   - Test (RED): `0244e8a` (test)
   - Implementation (GREEN): `84d6db8` (feat)

_Note: TDD task produced 2 commits (test → feat) following RED-GREEN cycle_

## Files Created/Modified
- `src/tools/__init__.py` - Exports search_notebook, NotebookLMTool, ToolError, ToolResult
- `src/tools/notebooklm.py` - Tool wrapper with retry logic and Claude SDK integration
- `tests/unit/test_notebooklm_tool.py` - 11 tests covering all tool functionality with mocks
- `tests/integration/__init__.py` - Integration test package structure

## Decisions Made

**1. Wrap nlm CLI as subprocess invocation**
- Rationale: notebooklm-mcp-cli provides `nlm` CLI tool for NotebookLM interaction
- Implementation: `subprocess.run(["nlm", "notebook", "query", notebook_id, query])`
- Benefit: Standard Python approach, no external MCP client library needed

**2. Return ToolResult on failure (not crash)**
- Rationale: Agent needs to handle tool failures gracefully and potentially retry or adjust strategy
- Implementation: ToolResult(success=False, error="详细错误信息") instead of raising exceptions
- Benefit: Agent receives error context and can continue workflow

**3. Retry logic respects config settings**
- Rationale: Network issues and transient failures are common with external tools
- Configuration: retry_count=3, retry_delay_sec=2, timeout_sec=120 from .env
- Implementation: Loop with sleep between retries, detailed error after exhaustion

**4. Chinese error messages for user-facing failures**
- Rationale: Target user base is Chinese-speaking
- Examples: "工具调用超时（120秒）", "NotebookLM搜索失败，已重试3次"
- Benefit: Better UX for Chinese users

**5. Tool schema compatible with Claude SDK**
- Rationale: Agent will use Claude SDK's tool use API
- Implementation: input_schema as JSON Schema, to_claude_tool() method
- Benefit: Seamless integration with Claude messages API in Phase 2

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation straightforward with TDD methodology.

## User Setup Required

**NotebookLM CLI installation:**
Users must install notebooklm-mcp-cli before using the tool:
```bash
pip install notebooklm-mcp-cli
```

Tool will return user-friendly error if nlm command not found:
"错误：未找到 nlm 命令。请先安装 notebooklm-mcp-cli: pip install notebooklm-mcp-cli"

## Next Phase Readiness

**Ready for Phase 1 Plan 4 (Integration: Wire CLI → Agent → Tool → Claude SDK)**

Tool wrapper complete and tested. Agent can now call NotebookLMTool to search NotebookLM via nlm CLI. Next step is to wire everything together: CLI receives topic, Agent uses Claude SDK with NotebookLM tool, and outputs results.

**Test coverage:** All 40 unit tests passing (11 new + 29 from previous plans)

**No blockers or concerns.**

---
*Phase: 01-foundation-setup*
*Completed: 2026-02-03*
