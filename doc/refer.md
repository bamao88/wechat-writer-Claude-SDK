# 项目初始化与状态管理规范

> 本规范定义了项目的物理结构、进度追踪方式以及产出物管理规则。

---

## 1. 最终项目目录结构 (直连版)

为了实现高性能"直连"，背景代码必须处在 Python 能够直接 `import` 的位置。

```
wechat-writer-openai-agents/
├── .env                # 环境变量配置
├── requirements.txt    # 项目依赖清单
├── main.py             # 业务执行入口 (Trace ID 生成)
├── agent.py            # Agent 大脑逻辑 (加载 prompts/ 下的提示词)
├── tools.py            # 工具定义层 (工具耗时采集)
├── notebooklm_tool.py  # NotebookLM 搜索工具 (集成 PleasePrompto/notebooklm-skill)
├── notebooklm_skill/   # [Git Submodule] NotebookLM Skill 仓库
│   └── scripts/
│       ├── run.py           # 脚本包装器
│       ├── auth_manager.py  # 认证管理
│       ├── notebook_manager.py  # 笔记本管理
│       └── ask_question.py  # 查询接口
├── logger.py           # 统一日志与追踪模块 (支持 Trace ID 并写入 logs/)
├── doc/                # 文档目录
│   ├── project-spec.md    # 项目规范与目录结构
│   ├── state.md           # 进度与状态管理
│   └── implementation-guide.md  # 分阶段实施指南
├── prompts/            # [New] 提示词目录 (版本管理，如 writer_v1.txt)
├── logs/               # [New] 日志目录 (存放持久化 Trace 日志)
├── output/             # 生成的文章与 Trace 报告 (JSON)
└── tests/              # 测试脚本目录
    ├── conftest.py          # Pytest 配置与路径设置
    ├── test_imports.py      # 依赖导入验证测试
    ├── test_logger.py       # Trace ID 生成测试
    ├── test_minimax_connection.py  # MiniMax 连接测试
    ├── test_notebooklm.py   # NotebookLM 搜索工具测试
    ├── test_tools.py        # 工具层与耗时采集测试
    ├── test_agent_tools.py  # Agent 工具挂载测试
    ├── test_main.py         # 主业务流程测试
    └── test_real.py         # 端到端真实 API 测试
```

---


## 4. 核心模块说明

| 模块 | 功能 | 关键函数/类 |
|------|------|-------------|
| `logger.py` | Trace ID 生成 | `create_trace_id()` |
| `agent.py` | Agent 工厂 | `create_agent()`, `create_agent_with_tools()`, `run_agent()` |
| `notebooklm_tool.py` | 搜索工具（集成 Skill） | `run_search()`, `setup_authentication()`, `list_notebooks()` |
| `notebooklm_skill/` | NotebookLM Skill | `auth_manager.py`, `notebook_manager.py`, `ask_question.py` |
| `tools.py` | 工具层 | `wrap_tool_with_latency()`, `get_registered_tools()`, `search_materials` |
| `main.py` | 业务流程 | `run_workflow()`, `save_report()` |
