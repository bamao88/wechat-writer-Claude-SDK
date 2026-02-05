# 项目参考（当前进度）

> 项目名：**wechat-writer-Claude-SDK**。基于 Claude SDK 的公众号写作助手，NotebookLM 作私域知识源，提示词统一放在 `prompts/`，不写在代码中。**当前只保留一套流程：洞察对齐。**

---

## 1. 当前目录结构

```
wechat-writer-Claude-SDK/
├── .env                    # 环境变量（LLM_PROVIDER、ANTHROPIC/OPENAI、NOTEBOOK_URL 等）
├── requirements.txt       # 项目依赖（anthropic, openai, python-dotenv, pypinyin 等）
├── main.py                # CLI 入口，固定走洞察对齐流程
│
├── prompts/               # 提示词目录（全部放这里，代码只做加载）
│   ├── README.md           # 目录规划与流程说明
│   ├── prompt_run.txt      # [已不用] 原单流程提示词，仅作参考保留
│   └── insight-alignment/  # 当前唯一流程：洞察对齐
│       ├── insight_specialist.txt   # 洞察顾问
│       ├── orchestrator.txt         # 总编辑
│       ├── knowledge_miner.txt      # 私域挖掘员
│       ├── web_researcher.txt       # 全网调研员（占位，工具未实现）
│       └── ghostwriter.txt          # 风格执笔人
│
├── notebooklm_skill/       # NotebookLM Skill（PleasePrompto/notebooklm-skill）
│   ├── .venv/              # Skill 独立环境
│   └── scripts/ask_question.py   # 查询入口（本项目 subprocess 调用）
│
├── scripts/
│   ├── test_anthropic_api.py   # Anthropic API 连通性测试
│   ├── test_llm_apis.py        # OpenAI + MiniMax API 测试
│   └── run_with_minimax.py     # 用 MINIMAX_* 跑完整流程
│
├── src/
│   ├── config/settings.py     # 配置（NOTEBOOK_URL、llm_provider 等）
│   ├── utils/                  # logger、prompt_loader
│   ├── cli/parser.py           # 命令行（仅 topic）
│   ├── tools/notebooklm.py    # NotebookLM 工具（Skill 方案）
│   ├── agent/
│   │   ├── __init__.py         # 仍暴露 run_agent 等，供脚本/测试用
│   │   ├── writer.py           # [已不用] 原单流程 Agent，仅作参考保留
│   │   ├── insight_alignment.py # 当前唯一流程入口
│   │   └── backends/           # LLM 多后端（Anthropic/MiniMax、OpenAI）
│   └── output/                 # create_output_dir、OutputTracer（thought_trace + article）
│
├── output/                 # 每次运行：YYYY-MM-DD_HHMMSS_slug_model-slug_shortid/
│   ├── thought_trace.md   # 流程轨迹
│   └── article.md         # 最终文章
│
├── doc/
│   ├── refer.md            # 本文件
│   ├── PROJECT_STRUCTURE.md   # 详细结构与配置
│   └── refer/
│       └── insight-alignment-architecture.md  # 洞察对齐架构设计
│
└── tests/unit/            # 单元测试（config、cli、notebooklm、output 等）
```

---

## 2. Agent 相关代码都在哪里

所有和「谁在调 LLM、谁在调工具、流程怎么串」相关的逻辑都在 **`src/agent/`** 下面，`main.py` 只负责解析选题、建输出目录、调用**洞察对齐**入口。

### 2.1 目录一览

| 路径 | 作用 | main.py 里的关系 |
|------|------|------------------|
| **`src/agent/insight_alignment.py`** | **当前唯一流程**：洞察顾问 → 总编辑 → 私域挖掘员(可选) → 风格执笔人 | `run_insight_alignment_flow()` |
| **`src/agent/backends/`** | **LLM 调用层**：发请求走这里（Anthropic/MiniMax 或 OpenAI） | insight_alignment 内部 `get_backend(config.llm_provider)` |
| **`src/agent/writer.py`** | 原单流程 Agent，**已不用**，仅作参考保留 | main.py 不再调用 |
| **`src/agent/__init__.py`** | 对外仍暴露 `run_agent`、`WritingAgent` 等 | 供脚本/测试用，main 不从这里导入流程 |

- **流程与编排**：看 `insight_alignment.py`。
- **模型请求与格式**：看 `src/agent/backends/`（`base.py` 定义接口，`anthropic_.py` / `openai_.py` 具体实现）。
- **工具**：NotebookLM 在 `src/tools/notebooklm.py`，由洞察顾问与私域挖掘员按需传入 backend。

### 2.2 当前流程用到的提示词

| 阶段 | 提示词文件（均在 `prompts/insight-alignment/`） |
|------|-----------------------------------------------|
| 洞察顾问 | `insight_specialist.txt` |
| 总编辑 | `orchestrator.txt` |
| 私域挖掘员 | `knowledge_miner.txt` |
| 风格执笔人 | `ghostwriter.txt` |

---

## 3. 流程与入口

**唯一流程：洞察对齐**

- **步骤**：用户选题 → 洞察顾问（NotebookLM）→ 总编辑（派单）→ 私域挖掘员(可选，NotebookLM) → 风格执笔人（成文）。
- **入口**：`python main.py "选题"`。
- **提示词**：全部在 `prompts/insight-alignment/*.txt`，由 `src/utils/prompt_loader.py` 按路径加载，**不写在代码里**。
- **输出目录名**：含选题拼音、**模型名**（如 MiniMax-M2-1）、短 id。

---

## 4. 核心模块与职责

| 模块 | 功能 |
|------|------|
| `main.py` | 解析 CLI（仅 topic），加载配置，创建输出目录与 tracer，调用 `run_insight_alignment_flow` |
| `src/agent/insight_alignment.py` | 洞察对齐：依次加载 insight_specialist / orchestrator / knowledge_miner / ghostwriter，解析总编辑派单，可选私域挖掘，最后执笔 |
| `src/agent/backends/` | 统一 LLM 接口；Anthropic（含 MiniMax Bearer）、OpenAI 两套后端 |
| `src/tools/notebooklm.py` | NotebookLM 工具（Skill subprocess），洞察顾问与私域挖掘员共用 |
| `src/output/` | 输出目录（含 model slug）、thought_trace.md、article.md |
| `src/utils/prompt_loader.py` | `load_prompt(name)`，支持子路径如 `insight-alignment/insight_specialist.txt` |

---

## 5. 配置要点

- **LLM**：`WECHAT_WRITER_LLM_PROVIDER` 或 `LLM_PROVIDER` = `anthropic`（默认）| `openai`；Anthropic 系用 `WECHAT_WRITER_ANTHROPIC_*`，OpenAI 系用 `OPENAI_*` 或 `WECHAT_WRITER_OPENAI_*`。
- **MiniMax**：用 Anthropic 兼容端点时，base_url 含 `minimax` 会自动走 Bearer 认证；可用 `scripts/run_with_minimax.py "选题"` 一键用 MiniMax 跑完整流程。
- **NotebookLM**：`NOTEBOOK_URL` 必填；`NOTEBOOKLM_SKILL_DIR` 可选（默认 `notebooklm_skill`）；Skill 需在目录内执行一次 `auth_manager.py setup`。

---

## 6. 当前进度小结

- **已完成**：只保留洞察对齐一套流程、LLM 多后端（Anthropic/MiniMax + OpenAI）、输出目录含模型名、提示词全部进 `prompts/insight-alignment/`。
- **未实现**：全网调研员（依赖全网搜索工具）；提示词效果需后续迭代优化。

更细的目录树、Phase 划分、配置表见 **doc/PROJECT_STRUCTURE.md**；架构设计见 **doc/refer/insight-alignment-architecture.md**。
