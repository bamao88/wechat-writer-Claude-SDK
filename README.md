# AI 写作助手 (wechat-writer-Claude-SDK)

基于 **NotebookLM** 资料与多后端 LLM（OpenAI / Azure / Anthropic）的公众号风格文章生成工具，支持两种流程：

- **Hub-Spoke 流程**（默认）：Planner → Miner/Web → Orchestrator → Writer → Critic（质量循环）
- **洞察对齐流程**：洞察顾问 → 总编辑 → 私域挖掘员 → 风格执笔人

一键输出 `article.md` 与 `thought_trace.md`。

## 功能概览

### 双流程架构

**1. Hub-Spoke 流程（默认，自动化）**
- Planner：策略决策（是否需要调研）
- Miner/Web：并行调研（私域资料 + 全网搜索）
- Orchestrator：生成逻辑大纲
- Writer：风格化写作
- Critic：质量评审与重写循环（最多3轮）
- 适合全自动化生成，带质量保证

**2. 洞察对齐流程（Insight-Alignment）**
- 洞察顾问（可调 NotebookLM）→ 总编辑 → 私域挖掘员（可选，多轮 NotebookLM）→ 风格执笔人
- 适合需要人工审核和迭代的场景

### 其他特性

- **多 LLM 后端**：OpenAI、Azure Responses API、Anthropic（含 MiniMax 等兼容端点）
- **NotebookLM 集成**：通过 [notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill) 子进程调用，基于你上传的笔记本做检索与引用
- **Web 搜索集成**：支持 Tavily API 进行全网实时搜索
- **命令行可选模型**：`-p openai -m gpt-5.2-chat` 指定 provider 与模型，不写则用 `.env`

## 环境要求

- Python 3.10+
- 项目依赖见 `requirements.txt`；NotebookLM Skill 需单独 `notebooklm_skill/.venv` 与认证（见下）

## 快速开始

### 1. 克隆与依赖

```bash
cd wechat-writer-Claude-SDK
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

复制并编辑 `.env`（可参考 `.env.example` 若存在）：

- **必填**：`NOTEBOOK_ID`、`NOTEBOOK_URL`（你的 NotebookLM 笔记本）
- **LLM**：选其一
  - **OpenAI / Azure**：`LLM_PROVIDER=openai`，`OPENAI_API_KEY`、`OPENAI_BASE_URL`（Azure 时含 `/openai/responses`）、`OPENAI_MODEL`
  - **Anthropic**：`LLM_PROVIDER=anthropic`，`ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL`
- **可选**：
  - `NOTEBOOKLM_SKILL_DIR` 指向 Skill 根目录（默认使用项目内 `notebooklm_skill`）
  - `TAVILY_API_KEY`：Tavily 搜索 API 密钥（Hub-Spoke 流程的 Web 搜索功能）

### 3. NotebookLM 认证（首次）

在 NotebookLM Skill 目录下完成登录，否则工具调用会报未认证：

```bash
cd notebooklm_skill
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
patchright install chrome
python scripts/auth_manager.py setup
```

按提示在浏览器中登录 Google / NotebookLM。详细步骤见 `notebooklm_skill/SETUP_AUTH_CN.md`。

### 4. 生成文章

**一条命令（推荐）：指定模型 + 选题**

```bash
# Hub-Spoke 流程（默认），指定 provider 和模型
python main.py -p openai -m gpt-5.2-chat "你的选题"

# Hub-Spoke 流程（默认），短选项
python main.py -p openai -m gpt-4o "如何做好时间管理"

# Hub-Spoke 流程（默认），使用 .env 中的 provider/model，仅传选题
python main.py "AI产品经理如何入门"

# 洞察对齐流程（需人工审核，需显式指定 --flow）
python main.py --flow insight-alignment "如何提升个人品牌"
```

**参数说明**

| 参数 | 说明 |
|------|------|
| `topic` | 文章选题（必填，位置参数） |
| `-p, --provider` | `openai` 或 `anthropic`，不填则用 `LLM_PROVIDER` |
| `-m, --model` | 模型名（如 `gpt-5.2-chat`），不填则用对应 env 中的 `*_MODEL` |
| `-f, --flow` | 流程类型：`hub-spoke`（默认，自动化）或 `insight-alignment`（人工审核） |

## 输出

每次运行会在 `output/` 下生成一个目录：

```
output/YYYY-MM-DD_HHMMSS_选题拼音_模型名_短id/
├── thought_trace.md   # 流程轨迹与中间输出
└── article.md         # 最终文章
```

## 脚本与测试

- `scripts/test_openai_tool_call.py`：OpenAI/Azure 工具调用往返测试（不依赖 NotebookLM）
- `scripts/test_notebooklm_tool.py`：NotebookLM 单次搜索测试（验证认证与检索）
- 单元测试：`pytest tests/unit/`

## 项目结构（简要）

```
├── main.py                 # CLI 入口（支持双流程）
├── requirements.txt
├── .env                    # 环境变量（不提交）
├── notebooklm_skill/       # NotebookLM Skill（认证与 ask_question）
├── prompts/
│   ├── insight-alignment/  # 洞察对齐流程提示词
│   └── hub-spoke/          # Hub-Spoke 流程提示词
├── src/
│   ├── agent/
│   │   ├── insight_alignment.py  # 洞察对齐流程
│   │   ├── hub_spoke/            # Hub-Spoke 架构（默认流程）
│   │   │   ├── flow.py          # 主入口函数
│   │   │   ├── executor.py      # 执行引擎（while 循环）
│   │   │   ├── state.py          # 状态数据类
│   │   │   ├── router.py         # 路由模块
│   │   │   └── workers/          # 各个 Worker (Planner, Miner, Web, etc.)
│   │   └── backends/        # LLM 多后端
│   ├── cli/                # 命令行解析
│   ├── config/             # 配置加载
│   ├── output/             # 输出目录与 tracer
│   ├── tools/              # NotebookLM、Web Search 工具封装
│   └── utils/
├── scripts/                # 测试与工具脚本
├── tests/
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── e2e/               # 端到端测试
└── doc/                    # 文档与架构说明
    ├── hub_spoke_实施计划_TDD.md   # Hub-Spoke TDD 实施计划
    └── hub_spoke_架构实现.md        # Hub-Spoke 架构文档（详细）
```

更多细节见 `doc/PROJECT_STRUCTURE.md`、`doc/refer.md`、`doc/hub_spoke_架构实现.md`。

## 许可证与参考

- NotebookLM Skill 见 [PleasePrompto/notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill)
- Azure Responses API 适配说明见 `doc/refer/OPENAI_ADAPTATION.md`
