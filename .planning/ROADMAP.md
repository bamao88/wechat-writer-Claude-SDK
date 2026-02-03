# Roadmap: AI 写作助手

## Overview

A Python CLI writing assistant that validates the complete "research -> plan -> write" loop using Claude SDK and NotebookLM integration. Three phases deliver: (1) CLI interface and tool integration foundation, (2) end-to-end agent workflow from research to article generation, (3) output management for all intermediate artifacts.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation Setup** - CLI entry point and NotebookLM tool integration
- [ ] **Phase 2: Agent Workflow** - Complete research-to-writing pipeline
- [ ] **Phase 3: Output System** - File persistence for all workflow stages

## Phase Details

### Phase 1: Foundation Setup
**Goal**: User can invoke the CLI and agent can call NotebookLM tools
**Depends on**: Nothing (first phase)
**Requirements**: CLI-01, NBK-01, NBK-02
**Success Criteria** (what must be TRUE):
  1. User can run `python main.py "选题"` and the process starts
  2. Agent can successfully call NotebookLM MCP Tool through Claude SDK (using notebooklm-mcp-cli: https://github.com/jacob-bd/notebooklm-mcp-cli)
  3. Agent receives and can process NotebookLM search results
**Plans**: 4 plans

Plans:
- [ ] 01-01-PLAN.md — TDD: Config loading + Logger (foundation utilities)
- [ ] 01-02-PLAN.md — TDD: CLI argument parsing with Chinese UX
- [ ] 01-03-PLAN.md — TDD: NotebookLM tool wrapper with retry logic
- [ ] 01-04-PLAN.md — Integration: Wire CLI -> Agent -> Tool -> Claude SDK

### Phase 2: Agent Workflow
**Goal**: Agent completes full research-outline-article generation loop
**Depends on**: Phase 1
**Requirements**: RSH-01, RSH-02, OTL-01, ART-01
**Success Criteria** (what must be TRUE):
  1. Agent can search NotebookLM based on user's topic and retrieve relevant materials
  2. Agent can synthesize search results into a structured research report
  3. Agent can generate an article outline based on research findings
  4. Agent can write a complete article following the generated outline
  5. Outline and article generation use existing prompts from `prompts/` directory (no new prompt generation logic required)
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Production prompt loading and workflow parameters
- [ ] 02-02-PLAN.md — End-to-end workflow verification (human verify)

### Phase 3: Output System ✅
**Goal**: Complete workflow trace and final article are saved to persistent files
**Depends on**: Phase 2
**Requirements**: OUT-01, OUT-02
**Success Criteria** (what must be TRUE):
  1. ✅ `thought_trace.md` captures the complete workflow execution in real-time: every agent output, tool call (name + parameters), and tool result, appended chronologically with timestamps/sequence numbers
  2. ✅ `article.md` contains the final complete article (title + body), extracted and saved when task completion is detected
  3. ✅ Output directory structure: `output/YYYY-MM-DD_HHMMSS_topic-slug_short-id/` with exactly two files: `thought_trace.md` and `article.md` (topic-slug via pypinyin, short-id prevents overwrites)
  4. ✅ All capture via tracer passed into agent loop - no reliance on model output markers
**Plans**: 03-01 implemented (output module + tracer + main wiring)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation Setup | 3/4 | In progress | - |
| 2. Agent Workflow | 0/2 | Planned | - |
| 3. Output System | 1/1 | Complete | 03-01 |
