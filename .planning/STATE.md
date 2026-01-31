# Project State: Multi LLM Provider Support

**Current Phase:** Phase 2 Complete ✓
**Last Updated:** 2026-01-31

## Project Reference

See: .planning/PROJECT.md (updated 2025-01-30)

**Core value:** 用户可以通过简单的命令行交互，选择一个或多个模型为同一选题生成文章
**Current focus:** Phase 3 - CLI and Multi-Model Runner

## Phase Status

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| 1: Provider Foundation | ✓ Complete | 2 | 100% |
| 2: Additional Providers | ✓ Complete | 4 | 100% |
| 3: CLI and Multi-Model Runner | ○ Planned | 3 | 0% |
| 4: Integration and Backward Compatibility | ○ Planned | 2 | 0% |

## Accumulated Context

### Roadmap Evolution

- Project initialized 2025-01-30
- 4 phases defined covering 16 requirements
- All phases planned with detailed PLAN.md files
- **Phase 1 completed** — Provider abstraction and MiniMax implementation done
- **Phase 2 completed** — All three providers (MiniMax, OpenAI, Claude) implemented and registered with real API integration tests

### Decisions Made

1. **Instance-based registry** — ProviderRegistry uses instance-level `_providers` dict to avoid test pollution
2. **Class-level provider classes** — `ProviderRegistry._provider_classes` is class-level for `from_env()` access
3. **Lazy model initialization** — Providers create model/client on first access
4. **Claude uses OpenAI-compatible format** — Third-party Claude proxies use OpenAI-compatible API format
5. **All providers registered together** — minimax, claude, openai all registered in unified registry
6. **Consistent provider pattern** — All providers follow identical structure: from_config() factory, lazy create_model(), config/display_name properties
7. **Environment-based configuration** — All providers load from environment variables with consistent naming convention (PROVIDER_API_KEY, PROVIDER_BASE_URL, PROVIDER_MODEL)
8. **Conditional test skipping** — Integration tests use `@pytest.mark.skipif` to gracefully skip when credentials are not configured
9. **Integration test marker** — Custom pytest marker registered in conftest.py to avoid warnings

### Open Questions

1. ~~Claude 第三方中转是否使用 OpenAI 兼容格式？~~ ✓ Resolved: Yes, uses OpenAI-compatible format
2. 是否需要并发执行多个模型？

## Current Position

**Phase:** 2 of 4 (Additional Providers) - Complete
**Plan:** 04 of 04 (Real API Testing) - Complete
**Status:** Complete
**Last activity:** 2026-01-31 - Completed phase-2-04 real API integration tests

Progress: [██████░░░░░░░░░░░░] 33% (4/12 plans complete)

---
