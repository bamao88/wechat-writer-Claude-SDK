# Roadmap: AI 写作助手

## Overview

A Python CLI writing assistant that validates the complete "research → plan → write" loop using Claude SDK and NotebookLM integration. Three phases deliver: (1) CLI interface and tool integration foundation, (2) end-to-end agent workflow from research to article generation, (3) output management for all intermediate artifacts.

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
**Plans**: TBD

Plans:
- [ ] 01-01: TBD during planning

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
**Plans**: TBD

Plans:
- [ ] 02-01: TBD during planning

### Phase 3: Output System
**Goal**: All workflow outputs are saved to persistent files with a clear directory and naming structure
**Depends on**: Phase 2
**Requirements**: OUT-01, OUT-02, OUT-03
**Success Criteria** (what must be TRUE):
  1. Research report is saved to file after research phase completes
  2. Article outline is saved to file after outline generation completes
  3. Final article is saved to file after writing completes
  4. Output directory structure: `output/YYYY-MM-DD_topic-slug_short-id/` with exactly three files: `research.md`, `outline.md`, `article.md` (topic-slug and short-id prevent overwrites when running same topic multiple times per day)
**Plans**: TBD

Plans:
- [ ] 03-01: TBD during planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation Setup | 0/TBD | Not started | - |
| 2. Agent Workflow | 0/TBD | Not started | - |
| 3. Output System | 0/TBD | Not started | - |
