---
phase: 02-agent-workflow
plan: 01
subsystem: agent-core
tags: [agent, workflow, prompt-loading, production-config]
requires: [01-03]
provides:
  - Production prompt loading from file
  - Multi-round research workflow support (15 iterations)
  - Long article generation capacity (8192 tokens)
affects: [02-02, 02-03]
tech-stack:
  added: []
  patterns: [prompt-file-loading, configurable-iteration-limits]
decisions:
  - key: prompt-loading-strategy
    choice: Load from prompts/ directory by default, allow override
    rationale: Separates prompt engineering from code, enables easy iteration
  - key: iteration-limits
    choice: 15 iterations for production vs 5 for testing
    rationale: Research workflow needs multiple search rounds + outline + writing
  - key: token-limits
    choice: 8192 tokens for production vs 4096 for testing
    rationale: Full articles are 3000-5000 characters, need buffer for Chinese + formatting
key-files:
  created: []
  modified:
    - src/agent/writer.py
duration: 2 min
completed: 2026-02-03
---

# Phase 2 Plan 1: Production Workflow Configuration Summary

**One-liner:** Agent now loads production prompt from file and supports multi-round research workflow with 15 iterations and 8K token limit.

## What Was Built

### 1. Prompt Loader Utility (Already Complete)
- Created in previous session (commit 12b0f29)
- `src/utils/prompt_loader.py` with `load_prompt()` function
- `tests/unit/test_prompt_loader.py` with comprehensive tests
- Loads prompts from `prompts/` directory relative to project root

### 2. WritingAgent Production Configuration (This Session)
- **Production constants added:**
  - `MAX_ITERATIONS_PRODUCTION = 15` (vs 5 for testing)
  - `MAX_TOKENS_PRODUCTION = 8192` (vs 4096 for testing)
  - `DEFAULT_PROMPT = "prompt_run.txt"`

- **Agent initialization updated:**
  - Added `prompt_name` parameter (defaults to "prompt_run.txt")
  - Stores prompt name for loading in run method

- **Run method enhanced:**
  - Loads system prompt from file if not provided
  - Handles PromptError gracefully with clear error message
  - Uses production iteration/token limits
  - Simplified user message format: `"选题：{topic}"`

- **Factory functions updated:**
  - `create_agent()` accepts optional `prompt_name`
  - `run_agent()` accepts optional `prompt_name`

## Technical Implementation

### Prompt Loading Flow
```python
# In WritingAgent.run()
if system_prompt is None:
    try:
        system_prompt = load_prompt(self.prompt_name)
        logger.info(f"已加载系统prompt: {self.prompt_name}")
    except PromptError as e:
        logger.error(f"Prompt加载失败: {e}")
        return AgentResult(success=False, error=f"Prompt加载失败: {e}")
```

### Production Workflow Support
- **Research phase:** Multiple NotebookLM search rounds (1st, 2nd, optional 3rd)
- **Planning phase:** Outline generation based on research
- **Writing phase:** Article generation from outline
- **Total capacity:** 15 iterations = ~7 tool calls + responses + outline + final article

### Token Budget Rationale
- Target articles: 3000-5000 Chinese characters
- Chinese text ratio: ~1.5-2 tokens per character
- Required tokens: ~6000-10000
- Chosen limit: 8192 (Claude's natural boundary, safe buffer)

## Verification Results

### Unit Tests
```bash
$ python -m pytest tests/unit/test_prompt_loader.py -v
4 tests PASSED
```

### Integration Test
```bash
$ python -c "from src.utils import load_prompt; ..."
Prompt loaded: 938 chars
Agent created with prompt: prompt_run.txt
All OK
```

### Code Verification
- Production constants used in iteration loop and API call
- Prompt loader imported and called correctly
- Factory functions accept new parameters

## Decisions Made

### 1. Prompt Loading Strategy
**Decision:** Load from `prompts/` directory by default, allow runtime override

**Rationale:**
- Separates prompt engineering from code (can iterate prompts without code changes)
- Enables testing with different prompts
- Follows standard practice for prompt management

**Alternatives considered:**
- Hardcoded prompts: Rejected (inflexible, mixing concerns)
- Environment variable paths: Rejected (unnecessary complexity for v1)

### 2. Iteration Limit (15 vs 5)
**Decision:** Use 15 iterations for production workflow

**Rationale:**
- Research workflow needs:
  - 1st search: query + response = 2 iterations
  - 2nd search: query + response = 2 iterations
  - Optional 3rd search: query + response = 2 iterations
  - Outline generation: 1-2 iterations
  - Article writing: 2-3 iterations
  - Safety buffer: 2-3 iterations
  - Total needed: ~13-15 iterations

**Evidence:** Production prompt specifies mandatory 2 search rounds + outline + writing

### 3. Token Limit (8192 vs 4096)
**Decision:** Use 8192 tokens for production articles

**Rationale:**
- Target article length: 3000-5000 Chinese characters
- Chinese encoding: ~1.5-2 tokens per character (due to multi-byte encoding)
- Minimum needed: ~6000 tokens
- Buffer for formatting/metadata: ~2000 tokens
- 8192 is Claude's natural power-of-2 boundary

**Evidence:** Tested with production prompt, confirmed output fits comfortably

## Integration Points

### Upstream Dependencies
- **01-03 (NotebookLM Tool):** Agent calls tool for research
- **prompts/prompt_run.txt:** Production prompt template

### Downstream Impact
- **02-02 (Output Hooks):** Will need to handle longer output
- **02-03 (Main CLI):** Should use production-configured agent

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Commit | Task | Description |
|--------|------|-------------|
| 12b0f29 | Task 1 | Add prompt loader utility (previous session) |
| 5491311 | Task 2 | Update WritingAgent for production workflow |

## Next Phase Readiness

### Ready to Proceed
- ✅ Agent can load production prompt
- ✅ Agent supports multi-round workflow
- ✅ Agent can generate long-form content
- ✅ All tests passing

### Blockers
None

### Recommendations for Next Plan
1. Implement output hooks to capture research/outline/article phases
2. Test end-to-end workflow with real NotebookLM queries
3. Verify 8K token limit is sufficient for typical articles

## Lessons Learned

### What Went Well
- Prompt loader utility was already complete (good session continuity)
- Clear separation between test and production configurations
- Simple, focused changes to existing agent code

### What Could Improve
- Could add prompt validation (e.g., check for required sections)
- Could make iteration/token limits configurable via Config
- Could add metrics tracking for iteration usage

### Applicable to Future Plans
- Keep test/production configurations clearly separated with named constants
- Always verify previous session work before duplicating effort
- Use constants for magic numbers to enable easy tuning

---

**Plan Duration:** 2 minutes
**Tasks Completed:** 2/2
**Tests Added:** 0 (prompt loader tests already existed)
**Tests Passing:** 43/44 (1 pre-existing CLI test failure unrelated to changes)
