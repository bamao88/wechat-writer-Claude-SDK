# 项目目录结构与进度

**生成时间:** 2026-02-03
**项目:** AI 写作助手 (wechat-writer-Claude-SDK)
**整体进度:** Phase 1–3 已完成；E2E 已跑通（单次检索 + 一次成文）

---

## 目录树

```
wechat-writer-Claude-SDK/
├── .env                           ✓ 环境变量（LLM_PROVIDER、ANTHROPIC/OPENAI 等，见下方配置说明）
├── .gitignore                     ✓ Git 忽略规则
├── requirements.txt               ✓ Python 依赖
├── main.py                        ✓ CLI 入口
│
├── prompts/                       ✓ 提示词目录
│   └── prompt_run.txt             ✓ 生产提示词（单次检索 · 一次成文）
│
├── notebooklm_skill/               ✓ NotebookLM Skill（PleasePrompto/notebooklm-skill）
│   ├── .venv/                     ✓ Skill 独立 Python 环境（patchright 等）
│   ├── data/                      ✓ 认证与 library（gitignore）
│   ├── scripts/
│   │   ├── ask_question.py        ✓ 查询入口（本项目 subprocess 调用）
│   │   ├── auth_manager.py        ✓ 认证
│   │   └── notebook_manager.py    ✓ 笔记本库
│   ├── requirements.txt           ✓ Skill 依赖
│   └── README.md / SKILL.md       ✓ 说明
│
├── scripts/                       ✓ 项目脚本
│   └── test_anthropic_api.py      ✓ Anthropic API 连通性测试
│
├── src/                           ✓ 源代码
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            ✓ 配置（含 notebooklm_skill_dir、llm_provider）
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── prompt_loader.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── parser.py
│   ├── tools/
│   │   ├── __init__.py
│   │   └── notebooklm.py          ✓ NotebookLM 工具（Skill 方案，优先 .venv/bin/python）
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── writer.py              ✓ 写作 Agent（按 config.llm_provider 选后端）
│   │   └── backends/              ✓ LLM 多后端
│   │       ├── __init__.py        ✓ get_backend(provider)
│   │       ├── base.py            ✓ 统一接口 BackendResponse / LLMBackend
│   │       ├── anthropic_.py      ✓ Anthropic + MiniMax（官方 Anthropic 兼容）
│   │       └── openai_.py         ✓ OpenAI / OpenAI 兼容端点
│   └── output/                    ✓ Phase 3 输出
│       ├── __init__.py            ✓ create_output_dir, topic_to_slug
│       └── tracer.py             ✓ thought_trace.md + article.md
│
├── tests/
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_logger.py
│   │   ├── test_prompt_loader.py
│   │   ├── test_cli.py
│   │   ├── test_notebooklm_tool.py
│   │   └── test_output.py         ✓ 输出目录与 tracer 单元测试
│   └── integration/
│       └── test_end_to_end.py
│
├── output/                        ✓ 每次运行创建子目录 YYYY-MM-DD_HHMMSS_slug_shortid/
│   └── .gitkeep
│
├── doc/
│   ├── refer.md
│   └── PROJECT_STRUCTURE.md       ✓ 本文件
│
└── .planning/
    ├── PROJECT.md
    ├── REQUIREMENTS.md
    ├── ROADMAP.md
    ├── STATE.md
    └── phases/
        ├── 01-foundation-setup/
        ├── 02-agent-workflow/
        └── 03-output-system/
```

---

## 按阶段分类的文件状态

### Phase 1: Foundation Setup（基础设施）— 75%

#### ✅ 01-01: Config + Logger
- `src/config/settings.py` — 配置加载（含 `NOTEBOOKLM_SKILL_DIR`）
- `src/utils/logger.py` — 日志
- 对应单元测试 ✓

#### ✅ 01-02: CLI Parser
- `src/cli/parser.py` — 命令行解析
- 对应单元测试 ✓

#### ✅ 01-03: NotebookLM Tool（Skill 方案）
- **实现方式：** 使用 [PleasePrompto/notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill)，subprocess 调用 `scripts/ask_question.py`
- **环境：** 优先使用 `notebooklm_skill/.venv/bin/python`，无则回退 `sys.executable`
- **配置：** `.env` 中 `NOTEBOOK_URL` 必填；`NOTEBOOKLM_SKILL_DIR` 可选（默认 `~/.claude/skills/notebooklm`，项目内即 `notebooklm_skill`）
- `src/tools/notebooklm.py` — 工具封装（解析 stdout、重试、超时）
- `tests/unit/test_notebooklm_tool.py` — 工具与 `_skill_python` 测试 ✓

#### ⚠️ 01-04: Integration
- `main.py`、`src/agent/writer.py` 已就绪，E2E 验证见 Phase 2

---

### Phase 2: Agent Workflow（工作流）— 已完成 ✓

#### ✅ 02-01: Production Prompt Loading
- `src/utils/prompt_loader.py`、`prompts/prompt_run.txt`
- `src/agent/writer.py` — 生产迭代数、token 上限、prompt 加载 ✓

#### ✅ 02-02: End-to-End Verification（已跑通）
- **Claude API：** 使用 `WECHAT_WRITER_ANTHROPIC_*`（优先于 shell 中的 `ANTHROPIC_BASE_URL` 等），官方 key 直连 `https://api.anthropic.com`
- **NotebookLM：** Skill 已配置（`notebooklm_skill/.venv`、认证、`ask_question.py`）
- **提示词：** `prompt_run.txt` 为「单次检索 · 一次成文」：第一条回复仅调用 1 次 `search_notebooklm`，收到结果后同轮完成分析 → 大纲 → 正文 → 标题

**E2E 验证步骤（复现用）：**

1. **前置**
   - Skill：`notebooklm_skill/.venv` 已建并装依赖，已执行 `notebooklm_skill/.venv/bin/python scripts/auth_manager.py setup`
   - `.env`：`NOTEBOOK_URL`、`WECHAT_WRITER_ANTHROPIC_*`（或 `ANTHROPIC_*`）已填且有效

2. **执行**
   ```bash
   cd /path/to/wechat-writer-Claude-SDK
   .venv/bin/python main.py "AI产品经理如何入门"
   ```
   （选题可换成与笔记本内容相关的主题）

3. **检查**
   - 工具：仅出现 1 次 `[工具] 调用 search_notebooklm...`，且无报错
   - 流程：第 1 轮 tool_use（搜索）→ 第 2 轮 end_turn（分析 + 大纲 + 正文 + 标题）
   - 输出：完整正文（第一人称、约 1500–3500 字）、文末单独一行标题；`output/` 下对应 run 目录内生成 `thought_trace.md` 与 `article.md`

---

### Phase 3: Output System（输出系统）— 已完成 ✓

- **输出目录：** CLI 启动时创建 `output/YYYY-MM-DD_HHMMSS_topic-slug_shortid/`（topic 转拼音 slug，short_id 防同秒覆盖）；创建失败则直接退出
- **thought_trace.md：** 实时追加；格式 `## [序号] [时间戳] 类型`；Agent 输出用 blockquote，工具调用用 code block，工具返回用 `<details>`（长结果前 500 字可见）；写入失败重试 3 次后缓冲，最后一次性写入
- **article.md：** 会话结束（end_turn）时写入最后一条 assistant 消息；写入失败重试 3 次，软失败（记录错误但不停流程）
- **实现：** `src/output/`（`create_output_dir`、`topic_to_slug`、`OutputTracer`）；`main.py` 创建 run_dir 并传入 tracer；`writer.run(tracer=...)` 在每轮响应与工具调用时调用 tracer
- **测试：** `tests/unit/test_output.py`

---

## 关键配置说明

### LLM 后端（provider）

| 变量 | 说明 |
|------|------|
| `WECHAT_WRITER_LLM_PROVIDER` 或 `LLM_PROVIDER` | `anthropic`（默认）或 `openai` |

- **anthropic**：使用 Anthropic 后端。适用于 Anthropic 官方 API 与 **MiniMax**（MiniMax 提供 [Anthropic 兼容](https://platform.minimaxi.com/docs/api-reference/text-anthropic-api)，只需改 base_url + api_key + model，无需单独后端）。
- **openai**：使用 OpenAI 后端，适用于 OpenAI 官方或第三方 OpenAI 兼容端点。

### Anthropic 后端（anthropic / MiniMax）

| 变量 | 说明 |
|------|------|
| `WECHAT_WRITER_ANTHROPIC_BASE_URL` | API 地址（Anthropic: `https://api.anthropic.com`；MiniMax: `https://api.minimaxi.com/anthropic`） |
| `WECHAT_WRITER_ANTHROPIC_API_KEY` | API Key |
| `WECHAT_WRITER_ANTHROPIC_MODEL` | 模型（Anthropic 如 `claude-haiku-4-5-20251001`；MiniMax 如 `MiniMax-M2.1`） |

未设置时回退到 `ANTHROPIC_*`。本项目优先读 `WECHAT_WRITER_*`，不受 shell 中 `ANTHROPIC_BASE_URL` 等影响。

### OpenAI 后端（openai）

| 变量 | 说明 |
|------|------|
| `WECHAT_WRITER_OPENAI_BASE_URL` 或 `OPENAI_BASE_URL` | API 地址（可选，第三方中转时必填） |
| `WECHAT_WRITER_OPENAI_API_KEY` 或 `OPENAI_API_KEY` | API Key |
| `WECHAT_WRITER_OPENAI_MODEL` 或 `OPENAI_MODEL` | 模型（如 `gpt-4o`） |

### NotebookLM Skill

| 变量 | 说明 |
|------|------|
| `NOTEBOOK_URL` | 笔记本 URL（必填） |
| `NOTEBOOKLM_SKILL_DIR` | Skill 根目录（可选；默认 `~/.claude/skills/notebooklm`，项目内即 `notebooklm_skill`） |

Skill 需在对应目录下执行一次认证（如 `notebooklm_skill/.venv/bin/python scripts/auth_manager.py setup`）。

---

## 核心模块与测试

| 文件 | 功能 |
|------|------|
| `main.py` | CLI 入口 |
| `src/config/settings.py` | 配置（含 `notebooklm_skill_dir`、`llm_provider`） |
| `src/utils/logger.py` | 日志 |
| `src/utils/prompt_loader.py` | Prompt 加载 |
| `src/cli/parser.py` | 命令行解析 |
| `src/tools/notebooklm.py` | NotebookLM（Skill 方案，优先 Skill .venv） |
| `src/agent/writer.py` | 写作 Agent（按 config.llm_provider 选后端，支持 tracer） |
| `src/agent/backends/` | LLM 多后端（Anthropic/MiniMax + OpenAI） |
| `src/output/` | 输出目录创建、thought_trace、article 持久化 |
| `scripts/test_anthropic_api.py` | Anthropic API 连通性测试 |

| 测试文件 | 测试对象 |
|---------|----------|
| `tests/unit/test_config.py` | Config |
| `tests/unit/test_logger.py` | Logger |
| `tests/unit/test_prompt_loader.py` | Prompt Loader |
| `tests/unit/test_cli.py` | CLI |
| `tests/unit/test_notebooklm_tool.py` | NotebookLM Tool（Skill） |
| `tests/unit/test_output.py` | 输出目录与 tracer |
| `tests/integration/test_end_to_end.py` | E2E（可选；可手动跑 `main.py "选题"` 验证） |

---

## 技术栈与外部依赖

### 项目依赖 (requirements.txt)

```
anthropic
python-dotenv
httpx
pytest
pypinyin
```

### NotebookLM

- **方案：** [notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill)（项目内 `notebooklm_skill/` 或 `NOTEBOOKLM_SKILL_DIR`）
- **运行：** subprocess 调用 `ask_question.py`，优先使用 Skill 目录下 `.venv/bin/python`
- **认证：** 在 Skill 目录内执行 `auth_manager.py setup` 一次

---

## 下一步建议

1. 按需优化提示词（`prompts/prompt_run.txt`）或扩展多轮检索流程
2. 回补 01-04 集成测试与 SUMMARY（可选）
3. 每次运行：`output/YYYY-MM-DD_HHMMSS_topic-slug_shortid/` 下生成 `thought_trace.md` 与 `article.md`

---

**最后更新:** 2026-02-03
