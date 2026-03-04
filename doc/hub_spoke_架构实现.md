# Hub-Spoke 架构实现文档

## 概述

Hub-Spoke 架构是一个自动化的文章生成流程，通过多个专业化的 Worker 协同工作，实现从选题到高质量文章的全自动生成。该架构的核心特点是：

- **中心化状态管理**：所有中间数据通过 State 对象传递
- **模块化 Worker**：每个 Worker 专注单一职责，易于测试和维护
- **质量保证循环**：Critic 自动评审并触发重写，最多3轮
- **降级输出策略**：即使未达标准，仍输出最佳结果并标记

## 架构图

### 1. 整体流程

```
                    ┌──────────────┐
                    │   Planner    │  决策：是否调研
                    └──────┬───────┘
                           │
          ┌────────────────┴────────────────┐
          │                                  │
     use_private                          use_web
          │                                  │
    ┌─────▼─────┐                     ┌─────▼─────┐
    │   Miner   │ 私域调研             │    Web    │ 全网搜索
    └─────┬─────┘                     └─────┬─────┘
          │                                  │
          └────────────────┬─────────────────┘
                           │
                    ┌──────▼──────┐
                    │ Orchestrator│  生成大纲
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Writer    │  风格化写作
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Critic    │  质量评审
                    └──────┬──────┘
                           │
                  ┌────────┴─────────┐
                  │                  │
              passed             failed
                  │                  │
            ┌─────▼─────┐      ┌────▼────┐
            │   Done    │      │ Rewrite │ (最多3次)
            └───────────┘      └────┬────┘
                                    │
                              回到 Writer
```

### 2. 模块结构

```
src/agent/hub_spoke/
├── flow.py                     # 主入口：run_hub_spoke_flow()
├── executor.py                 # 执行引擎：while 循环 + 状态机
├── state.py                    # 状态数据类：State
├── router.py                   # 路由逻辑：determine_next_step()
├── tools.py                    # 工具工厂：create_tools()
└── workers/
    ├── __init__.py            # Worker 工厂：create_workers()
    ├── planner.py             # Planner Worker：策略决策
    ├── miner.py               # Miner Worker：私域调研
    ├── web.py                 # Web Worker：全网搜索
    ├── orchestrator.py        # Orchestrator Worker：生成大纲
    ├── writer.py              # Writer Worker：风格化写作
    └── critic.py              # Critic Worker：质量评审
```

## 核心组件

### 1. State（状态中心）

State 是整个流程的数据中心，记录所有中间产物和控制流信息：

```python
@dataclass
class State:
    # 输入
    topic: str                          # 选题
    user_context: str = ""              # 用户上下文（可选）

    # Planner 决策
    use_private: bool = False           # 是否调研私域
    use_web: bool = False               # 是否调研全网
    planner_reason: str = ""            # 决策理由

    # 调研材料（Miner 双层输出）
    structured_points: List[str] = []   # 结构化观点（给 Orchestrator）
    raw_voice_clips: List[str] = []     # 原始语料（给 Writer）

    # Web 调研结果
    web_research: str = ""              # 全网搜索结果

    # 写作中间产物
    outline: str = ""                   # 大纲（Orchestrator 生成）
    draft: str = ""                     # 草稿（Writer 生成）

    # 质量评审与回溯
    critic_score: int = 0               # Critic 评分 (0-10)
    critic_reason: str = ""             # 评分理由
    critic_feedback: str = ""           # 修改建议
    iteration_count: int = 0            # 重写轮次

    # 系统状态
    next_step: str = "planner"          # 下一步执行的 Worker
    status: str = "PENDING"             # 整体状态
```

### 2. Executor（执行引擎）

Executor 实现主控制循环，负责：
- 根据 `state.next_step` 路由到相应 Worker
- 处理 Critic 反馈和重写循环
- 管理降级输出（max_iterations=3）

```python
def run(state, workers, tools, backend, tracer):
    state.status = "IN_PROGRESS"

    while state.next_step != "done":
        if state.next_step == "planner":
            workers["planner"].run(state, backend, tracer)
            state.next_step = determine_next_step(state, "")

        elif state.next_step == "writer":
            workers["writer"].run(state, backend, tracer)
            state.next_step = "critic"

        elif state.next_step == "critic":
            result = workers["critic"].run(state)
            tracer.append_critic_result(...)

            if result.passed:
                tracer.save_article(state.draft, degraded=False)
                state.next_step = "done"
            elif state.iteration_count >= MAX_ITERATIONS:
                tracer.save_article(state.draft, degraded=True)
                state.next_step = "done"
            else:
                state.critic_feedback = result.reason
                state.iteration_count += 1
                state.next_step = "writer"  # 回溯

        # ... 其他 Worker 处理

    return state
```

### 3. Router（路由模块）

Router 负责状态机转换逻辑：

```python
def determine_next_step(state: State, agent_output: str) -> str:
    """根据当前状态决定下一步."""
    current = state.next_step

    if current == "planner":
        if state.use_private:
            return "miner"
        elif state.use_web:
            return "web"
        else:
            return "orchestrator"

    elif current == "miner":
        return "web" if state.use_web else "orchestrator"

    elif current == "web":
        return "orchestrator"

    elif current == "orchestrator":
        return "writer"

    elif current == "writer":
        return "critic"

    # Critic 的转换由 Executor 处理
    return "done"
```

## Worker 职责说明

### Planner（策略决策者）

**职责**：根据选题和用户上下文，决定调研策略

**输入**：
- `state.topic`：选题
- `state.user_context`：用户提供的上下文（可选）

**输出**：JSON 格式
```json
{
  "use_private": true,
  "use_web": false,
  "reason": "用户未提供足够上下文，需要调研私域资料"
}
```

**决策规则**：
- 用户上下文 ≥300 字 → 可跳过调研（both=false）
- 否则 → 至少调研私域或全网

### Miner（私域挖掘员）

**职责**：从 NotebookLM 私域资料中检索相关内容

**输入**：
- `state.topic`：选题
- `notebooklm_tool`：NotebookLM 工具实例

**输出**：双层 JSON 格式
```json
{
  "structured_points": [
    "个人品牌的核心是价值定位",
    "需要持续输出专业内容"
  ],
  "raw_voice_clips": [
    "我一直强调，做个人品牌最重要的是找到自己的独特价值",
    "内容输出要有规律性，不能三天打鱼两天晒网"
  ]
}
```

**特点**：
- `structured_points` 传给 Orchestrator 用于逻辑排布
- `raw_voice_clips` 传给 Writer 用于风格模仿
- 输出总长度 ≤500 字（上下文裁剪）

### Web（全网搜索员）

**职责**：通过 Tavily API 搜索全网实时内容

**输入**：
- `state.topic`：选题
- `web_tool`：Web 搜索工具实例

**输出**：
```
state.web_research = "搜索结果摘要..."
```

**特点**：
- 结果截断至 ≤500 字
- 错误时返回空字符串（不阻塞流程）

### Orchestrator（逻辑编排者）

**职责**：根据调研材料生成紧凑的逻辑大纲

**输入**：
- `state.structured_points`：结构化观点（来自 Miner）
- `state.web_research`：全网搜索结果（来自 Web）

**输出**：
```markdown
# 如何提升个人品牌

## 核心观点
1. 明确个人价值定位
2. 持续输出专业内容
3. 建立个人影响力

## 论据支撑
- 价值定位是品牌基础
- 内容输出需要规律性
- 影响力来自长期积累
```

**约束**：
- 输出长度 ≤800 字
- 仅包含逻辑骨架，不展开细节

### Writer（风格执笔人）

**职责**：根据大纲和语料，生成风格化的完整文章

**输入**：
- `state.outline`：大纲（来自 Orchestrator）
- `state.raw_voice_clips`：原始语料（来自 Miner，用于风格模仿）
- `state.critic_feedback`：修改建议（可选，重写时提供）
- `state.iteration_count`：当前轮次

**输出**：
```
state.draft = "完整的文章内容..."
```

**特点**：
- 模仿 `raw_voice_clips` 中的语气和措辞
- 如果有 `critic_feedback`，则针对性修改
- 目标长度 ≥800 字

**重写逻辑**：
```python
if state.iteration_count > 0:
    system_prompt += f"""

上一轮审稿意见：{state.critic_feedback}
请针对以上问题修改，其余部分保持原有风格。
"""
```

### Critic（质量评审员）

**职责**：对文章进行规则检查，决定是否通过或需要重写

**输入**：
- `state.draft`：文章草稿
- `state.outline`：大纲（用于检查覆盖度）

**输出**：
```python
@dataclass
class CriticResult:
    score: int          # 评分 0-10
    passed: bool        # score >= 7 为通过
    reason: str         # 理由或修改建议
```

**检查规则**：
1. **字数检查**：正文 ≥800 字
2. **结构完整性**：包含标题、引言、正文段落、结尾
3. **大纲覆盖度**：大纲中的核心论点在正文中均有体现

**评分逻辑**：
- 全部通过：8-10 分（passed=True）
- 部分问题：5-7 分（passed=False）
- 严重问题：0-4 分（passed=False）

## 数据流示例

### 完整流程（全量调研 + 一次通过）

```
1. Planner 决策
   Input: topic="如何提升个人品牌"
   Output: use_private=true, use_web=true

2. Miner 调研
   Input: topic="如何提升个人品牌"
   Tool: NotebookLM.search("个人品牌 提升")
   Output:
     structured_points=["价值定位", "持续输出"]
     raw_voice_clips=["我一直强调...", "内容输出要有..."]

3. Web 搜索
   Input: topic="如何提升个人品牌"
   Tool: Tavily.search("个人品牌建设 2026")
   Output: web_research="最新趋势..."

4. Orchestrator 编排
   Input: structured_points + web_research
   Output: outline="# 如何提升个人品牌\n## 核心观点..."

5. Writer 写作
   Input: outline + raw_voice_clips
   Output: draft="# 如何提升个人品牌\n\n在当今时代..."

6. Critic 评审
   Input: draft + outline
   Check: 字数=1200✓, 结构完整✓, 覆盖大纲✓
   Output: score=9, passed=true, reason="文章质量优秀"

7. 完成
   Save: article.md (degraded=false)
```

### 重写流程（第一轮未通过）

```
5. Writer 写作（第一轮）
   Input: outline + raw_voice_clips
   Output: draft="..." (字数仅600字)

6. Critic 评审（第一轮）
   Check: 字数=600✗ (未达800)
   Output: score=6, passed=false, reason="字数不足，需扩充论据"

   → iteration_count=1, next_step="writer"

5. Writer 写作（第二轮）
   Input: outline + raw_voice_clips + critic_feedback="字数不足..."
   Output: draft="..." (扩充至1100字)

6. Critic 评审（第二轮）
   Check: 字数=1100✓, 结构完整✓, 覆盖大纲✓
   Output: score=8, passed=true

7. 完成
   Save: article.md (degraded=false)
```

### 降级输出（3轮均未通过）

```
循环3次：Writer → Critic (failed)

第3轮后:
   iteration_count=3 >= MAX_ITERATIONS
   → 保存当前最佳版本，标记 degraded=true
   → article.md 文件头部添加警告：

   ⚠️ 本文档为降级输出（质量未达标准）
   - Critic 评分：6/10
   - 理由：字数不足，论据薄弱
   - 重写轮次：3/3（已达上限）
```

## Trace 文件示例

完整流程执行后，`thought_trace.md` 包含：

```markdown
# 流程轨迹

## [Planner] 策略决策
**时间**: 2026-02-26 20:30:15

### 输入
选题：如何提升个人品牌

### 输出
```json
{
  "use_private": true,
  "use_web": false,
  "reason": "需要调研私域资料库中的个人品牌相关内容"
}
```

## [Miner] 私域调研
**时间**: 2026-02-26 20:30:20

### 工具调用
- search_notebooklm(query="个人品牌 提升 价值定位")

### 输出
```json
{
  "structured_points": [
    "个人品牌的核心是价值定位",
    "需要持续输出专业内容"
  ],
  "raw_voice_clips": [
    "我一直强调，做个人品牌最重要的是找到自己的独特价值",
    "内容输出要有规律性，不能三天打鱼两天晒网"
  ]
}
```

## [Orchestrator] 逻辑排布
**时间**: 2026-02-26 20:30:35

### 输出
# 如何提升个人品牌

## 核心观点
1. 明确个人价值定位
...

## [Writer] 风格化写作
**时间**: 2026-02-26 20:30:50

### 输出
# 如何提升个人品牌

在当今时代，个人品牌变得越来越重要...
（完整文章省略）

## [Critic] 质量评审

| 轮次 | 评分 | 状态 | 原因 |
|-----|------|------|------|
| 1   | 9    | ✓ 通过 | 文章结构完整，论据充分，风格自然 |

---

## 总结
- 工具调用次数：1
- 重写轮次：0
- 最终状态：COMPLETED
- 输出质量：正常
```

## 使用指南

### 1. 基本使用

```bash
# 使用 Hub-Spoke 流程生成文章
python main.py --flow hub-spoke "如何提升个人品牌"

# 指定 provider 和 model
python main.py -f hub-spoke -p openai -m gpt-4o "AI产品经理职业发展"
```

### 2. 配置 Tavily API（可选）

如果需要使用 Web 搜索功能，在 `.env` 中添加：

```bash
TAVILY_API_KEY=your_tavily_api_key
```

没有配置时，Web Worker 会跳过搜索，不影响流程。

### 3. 查看输出

```bash
output/2026-02-26_203015_如何提升个人品牌_gpt-4o_abc123/
├── thought_trace.md   # 完整流程轨迹
├── article.md         # 最终文章
└── agent_inputs.json  # 所有 Agent 输入记录（用于调试）
```

### 4. 降级输出说明

当文章经过3轮重写仍未通过 Critic 检查时，系统会：
1. 保存当前最佳版本到 `article.md`
2. 在文件头部添加 `⚠️` 警告标记
3. 标记 `HubSpokeResult.degraded = True`
4. 在 trace 中记录详细原因

这确保即使质量未达标，仍能获得可用的输出。

## 测试

```bash
# 运行所有 Hub-Spoke 相关测试
pytest tests/unit/hub_spoke/ -v
pytest tests/integration/test_executor.py -v
pytest tests/e2e/test_hub_spoke_flow.py -v

# 单独测试某个 Worker
pytest tests/unit/hub_spoke/test_planner.py -v
pytest tests/unit/hub_spoke/test_critic.py -v
```

## 性能指标

**基准场景**（单次完整流程，无重写）：
- **总耗时**：2-5 分钟
- **工具调用**：NotebookLM 1-3 次，Web 0-3 次
- **Token 消耗**：30k-50k tokens（含所有 Agent 调用）
- **Trace 文件大小**：200-500 KB

**重写场景**（2轮重写）：
- **总耗时**：+2-3 分钟/轮
- **Token 消耗**：+10k-15k tokens/轮

## 与 Insight-Alignment 对比

| 特性 | Insight-Alignment | Hub-Spoke |
|------|------------------|-----------|
| **流程复杂度** | 简单（4步） | 复杂（6步+循环） |
| **自动化程度** | 半自动（需人工审核） | 全自动 |
| **质量保证** | 人工判断 | 自动 Critic + 重写循环 |
| **调研方式** | 仅私域（NotebookLM） | 私域 + 全网搜索 |
| **输出策略** | 直接输出 | 降级策略（保证输出） |
| **适用场景** | 需要人工介入和迭代 | 批量生成、自动化流程 |
| **测试覆盖** | 基础 | 完整（单元+集成+E2E） |

## 扩展方向

1. **并行调研优化**：使用 `asyncio.gather` 同时调用 Miner+Web
2. **Critic 升级**：从规则检查升级为 LLM 评审
3. **动态循环次数**：根据 Critic 反馈质量调整 MAX_ITERATIONS
4. **更多 Web 工具**：支持 SerpAPI、Google Custom Search
5. **A/B 测试框架**：对比两种 flow 的输出质量
6. **缓存机制**：NotebookLM/Web 结果缓存，避免重复查询
7. **流式输出**：Writer 生成时实时展示进度

## 参考文档

- TDD 实施计划：`doc/hub_spoke_实施计划_TDD.md`
- Phase 完成总结：`doc/phase3_completion_summary.md`
- 架构分层迭代计划：`doc/架构分层迭代计划.md`
