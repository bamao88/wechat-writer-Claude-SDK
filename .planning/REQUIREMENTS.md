# Requirements: Multi LLM Provider Support

**Defined:** 2025-01-30
**Core Value:** 用户可以通过简单的命令行交互，选择一个或多个模型为同一选题生成文章

## v1 Requirements

### Provider 抽象层

- [x] **PROV-01**: 定义 LLMProvider 抽象基类，统一接口
- [x] **PROV-02**: 实现 MiniMaxProvider（迁移现有功能）
- [x] **PROV-03**: 实现 OpenAIProvider（支持第三方中转）
- [x] **PROV-04**: 实现 ClaudeProvider（支持第三方中转）
- [x] **PROV-05**: 实现 ProviderRegistry 管理所有 Provider

### 配置管理

- [x] **CONF-01**: 支持 .env 配置多 Provider（API key、base_url、model）
- [x] **CONF-02**: 配置验证，检查必需字段
- [x] **CONF-03**: 运行时从环境变量加载所有可用 Provider

### CLI 交互

- [ ] **CLI-01**: 交互式模型选择（单选/多选/全选）
- [ ] **CLI-02**: 显示可用模型列表
- [ ] **CLI-03**: 支持命令行参数指定模型（非交互式）

### 多模型运行

- [ ] **RUN-01**: 支持串行运行多个模型
- [ ] **RUN-02**: 每个模型独立生成文章并保存
- [ ] **RUN-03**: 输出汇总报告（各模型状态、输出路径）

### 向后兼容

- [ ] **COMPAT-01**: 现有 main.py 接口保持可用
- [ ] **COMPAT-02**: 无参数时默认行为不变（使用 MiniMax）

## v2 Requirements

### 性能优化

- **PERF-01**: 支持并发运行多个模型
- **PERF-02**: 添加超时控制

### 输出增强

- **OUT-01**: 生成对比报告（各模型输出摘要）
- **OUT-02**: 支持自定义输出文件名模板

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI | 保持 CLI 工具定位 |
| 模型自动评分 | 用户自行判断质量 |
| 非 OpenAI 兼容格式 | 第三方中转通常都提供兼容格式 |
| 流式输出 | 保持现有批量模式 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROV-01 | Phase 1 | Complete |
| PROV-02 | Phase 1 | Complete |
| PROV-03 | Phase 2 | Complete |
| PROV-04 | Phase 2 | Complete |
| PROV-05 | Phase 1 | Complete |
| CONF-01 | Phase 1 | Complete |
| CONF-02 | Phase 1 | Complete |
| CONF-03 | Phase 1 | Complete |
| CLI-01 | Phase 3 | Pending |
| CLI-02 | Phase 3 | Pending |
| CLI-03 | Phase 3 | Pending |
| RUN-01 | Phase 3 | Pending |
| RUN-02 | Phase 3 | Pending |
| RUN-03 | Phase 3 | Pending |
| COMPAT-01 | Phase 4 | Pending |
| COMPAT-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Phase 1 Complete: 7 requirements
- Remaining: 8 requirements
- Unmapped: 0 ✓

---
*Requirements defined: 2025-01-30*
*Last updated: 2025-01-30 after Phase 1 completion*
