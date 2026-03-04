# Hub-and-Spoke 架构实施计划（测试驱动）

## 一、可行性分析

### 1.1 现有架构 vs 提议架构对比

#### **当前实现** (`insight_alignment.py`)
```
洞察顾问 → 总编辑R1 → 私域挖掘员 → 总编辑R2 → 风格执笔人
```
- ✅ 已有：双轮制编排、总编辑决策路由、XML解析+降级
- ✅ 已有：NotebookLM工具集成、完整的OutputTracer
- ✅ 已有：多后端抽象(Anthropic/OpenAI/MiniMax/Azure)
- ❌ 缺失：Planner策略层、Web调研工具、Critic质量评审、重写循环

#### **提议架构** (架构分层迭代计划.md)
```
Planner → Miner/Web(并行) → Orchestrator → Writer → Critic(循环≤3次)
```
- 🆕 新增：Planner决定调研路径(use_private/use_web)
- 🆕 新增：Web调研工具(Tavily/SerpAPI)
- 🆕 新增：Critic规则检查 + 重写循环
- 🆕 新增：State状态中心 + Router路由模块 + Executor执行引擎
- 🔄 改造：Miner双层输出(structured_points + raw_voice_clips)

---

### 1.2 可行性评估

| 组件 | 难度 | 可行性 | 说明 |
|------|------|--------|------|
| **Planner Agent** | 🟢 低 | ✅ 高 | 复用现有Agent模式，新增prompt + JSON解析 |
| **State 数据类** | 🟢 低 | ✅ 高 | 定义dataclass，线程化传递 |
| **Router 模块** | 🟢 低 | ✅ 高 | 提取现有XML解析逻辑到独立模块 |
| **Executor 引擎** | 🟡 中 | ✅ 高 | 从函数式改为while循环，需重构控制流 |
| **Web 工具集成** | 🟡 中 | ✅ 高 | 参考NotebookLMTool实现Tavily/SerpAPI封装 |
| **Critic Agent** | 🟢 低 | ✅ 高 | 规则检查(字数/结构/关键字段)为Python代码 |
| **重写循环** | 🟡 中 | ✅ 高 | 在Executor的while循环中实现回溯逻辑 |
| **并行调研** | 🟠 中-高 | ⚠️ 中 | 可先用顺序执行，后续优化为asyncio并行 |
| **上下文裁剪** | 🟢 低 | ✅ 高 | 在各Worker的system prompt中加约束即可 |
| **Tracer扩展** | 🟢 低 | ✅ 高 | 已有扩展点，新增append_critic_result等方法 |

**总体可行性：✅ 高（90%+）**

---

### 1.3 关键架构决策

#### **决策1：迁移策略**
- ❌ **方案A**：原地重构`insight_alignment.py`（风险高，破坏现有功能）
- ✅ **方案B**：新建`hub_spoke_flow.py`作为独立流程（安全，可并行测试）
- **推荐**：方案B，保留现有流程，新架构在`src/agent/hub_spoke/`目录下独立开发

#### **决策2：并行执行**
- ❌ **方案A**：真正异步（asyncio.gather同时调用Miner+Web）
- ✅ **方案B**：顺序执行 + 进度跟踪（先实现，后优化）
- **推荐**：方案B，MVP阶段顺序调用，Phase 2优化为并行

#### **决策3：State管理**
- 当前：消息链传递（messages列表）
- 提议：State数据类（集中式状态）
- **推荐**：State + Messages双轨制，State作为元数据中心，Messages保留LLM上下文

---

## 二、测试驱动实施计划

### 2.1 总体策略

**TDD原则**：
1. **红-绿-重构**：先写失败测试 → 最小实现 → 重构优化
2. **自底向上**：从最小单元(Router/State)到集成(Executor/Flow)
3. **隔离测试**：每个模块独立可测，使用Mock避免外部依赖
4. **端到端验证**：最后阶段进行完整流程测试

**测试层次**：
- **单元测试**：Router, State, Critic规则检查, Tracer扩展
- **集成测试**：Executor循环逻辑, Agent调用链, Tool集成
- **端到端测试**：完整hub_spoke_flow从topic到article

---

### 2.2 六阶段实施路线图

---

### **Phase 1: 基础设施** (预计2-3天)

#### 目标
建立测试框架、核心数据结构、路由模块

#### 任务清单

**1.1 测试框架搭建**
- [ ] 安装pytest + pytest-mock + pytest-asyncio
- [ ] 创建`tests/`目录结构：
  ```
  tests/
  ├── unit/
  │   ├── test_state.py
  │   ├── test_router.py
  │   └── test_critic.py
  ├── integration/
  │   ├── test_executor.py
  │   └── test_workers.py
  └── e2e/
      └── test_hub_spoke_flow.py
  ```
- [ ] 编写conftest.py（fixtures for mock backend, mock tools）

**1.2 State数据类** (`src/agent/hub_spoke/state.py`)
- [ ] **测试先行**：`tests/unit/test_state.py`
  - 测试State初始化（topic必填，其他字段有默认值）
  - 测试字段类型验证
  - 测试State序列化/反序列化（dataclasses.asdict）
- [ ] **实现**：定义State dataclass（参考架构文档第十节字段定义）
  ```python
  @dataclass
  class State:
      # 输入
      topic: str
      user_context: str = ""
      # Planner决策
      use_private: bool = False
      use_web: bool = False
      planner_reason: str = ""
      # 调研素材（Miner双层输出）
      structured_points: list[str] = field(default_factory=list)
      raw_voice_clips: list[str] = field(default_factory=list)
      # Web调研结果
      web_research: str = ""
      # 写作中间产物
      outline: str = ""
      draft: str = ""
      # 质量评审与回溯
      critic_score: int = 0
      critic_reason: str = ""
      critic_feedback: str = ""
      iteration_count: int = 0
      # 系统状态
      next_step: str = "planner"
      status: str = "PENDING"
  ```

**1.3 Router路由模块** (`src/agent/hub_spoke/router.py`)
- [ ] **测试先行**：`tests/unit/test_router.py`
  - 测试XML信号提取：`<status>PASS</status>` → "PASS"
  - 测试XML解析失败时的降级（返回None或默认值）
  - 测试多种status信号（PASS, NEED_REWRITE, ERROR）
- [ ] **实现**：提取现有`insight_alignment.py`的XML解析逻辑
  ```python
  def parse_status_signal(output: str) -> Optional[str]:
      """从输出中提取<status>标签，支持正则降级"""
      pass

  def determine_next_step(state: State, agent_output: str) -> str:
      """根据当前状态和Agent输出决定next_step"""
      pass
  ```

**1.4 增强OutputTracer** (`src/output/tracer.py`)
- [ ] **测试先行**：`tests/unit/test_tracer_extensions.py`
  - 测试`append_critic_result(cycle, score, passed, reason)`写入格式
  - 测试`save_article(content, degraded=True)`在文件头部添加警告
  - 测试`_generate_summary`增加重写轮次统计列
- [ ] **实现**：扩展现有OutputTracer类
  ```python
  def append_critic_result(self, cycle: int, score: int, passed: bool, reason: str):
      # 按表格格式写入| Cycle | 评分 | 状态 | 原因 |
      pass

  def save_article(self, content: str, degraded: bool = False):
      # 如果degraded=True，在文件头部添加⚠️标记
      pass
  ```

**验收标准**：
- [x] 所有Phase 1单元测试通过（pytest coverage ≥90%）
- [x] State可序列化为JSON（用于调试）
- [x] Router能正确解析现有orchestrator.txt的XML输出
- [x] Tracer扩展方法可正常写入trace文件

---

### **Phase 2: 核心Agent** (预计3-4天)

#### 目标
实现Planner和Critic两个新Agent

#### 任务清单

**2.1 Planner Agent** (`src/agent/hub_spoke/workers/planner.py`)
- [ ] **提示词设计**：`prompts/hub-spoke/planner.txt`
  - 输入：选题 + 用户上下文(可选)
  - 输出：JSON格式 `{"use_private": bool, "use_web": bool, "reason": str}`
  - 约束：仅当用户提供≥300字上下文时允许both=false
- [ ] **测试先行**：`tests/unit/test_planner.py`
  - Mock backend返回各种JSON决策，测试解析逻辑
  - 测试4种路径决策（纯AI/只私域/只全网/全量调研）
  - 测试JSON解析失败时的降级处理
- [ ] **实现**：PlannerWorker类
  ```python
  class PlannerWorker:
      def run(self, state: State, backend, tracer) -> PlannerResult:
          # 调用backend.create，解析JSON输出
          # 更新state.use_private, use_web, planner_reason
          pass
  ```

**2.2 Critic Agent** (`src/agent/hub_spoke/workers/critic.py`)
- [ ] **规则检查逻辑**
  - 字数检查：正文≥800字
  - 结构完整性：包含标题/引言/正文段落/结尾
  - 关键字段：大纲中的核心论点在正文中均有体现
- [ ] **测试先行**：`tests/unit/test_critic.py`
  - 测试各项规则单独触发（mock不同的draft）
  - 测试评分逻辑（passed=score≥7）
  - 测试输出格式：`{"score": int, "passed": bool, "reason": str}`
- [ ] **实现**：CriticWorker类（纯代码规则，不调用LLM）
  ```python
  class CriticWorker:
      def run(self, state: State) -> CriticResult:
          # 规则检查state.draft和state.outline
          # 返回评分结果
          pass
  ```

**2.3 提示词管理**
- [ ] 创建`prompts/hub-spoke/`目录
- [ ] 编写4个Agent的prompt模板：
  - `planner.txt`：策略决策，输出JSON
  - `miner.txt`：双层输出(structured_points + raw_voice_clips)
  - `orchestrator.txt`：逻辑排布，输出紧凑大纲(≤800字)
  - `writer.txt`：风格化写作，接收critic_feedback条件块

**验收标准**：
- [x] Planner能正确解析4种路径决策
- [x] Critic规则检查准确率100%（在测试用例上）
- [x] 提示词符合上下文裁剪约束（Miner/Web输出≤500字，Orchestrator输出≤800字）

---

### **Phase 3: 工具集成** (预计2-3天)

#### 目标
实现Web调研工具(Tavily/SerpAPI)

#### 任务清单

**3.1 Web工具抽象** (`src/tools/web_search.py`)
- [ ] **接口定义**：参考NotebookLMTool模式
  ```python
  class WebSearchTool:
      name = "search_web"
      description = "搜索全网实时热点、行业数据与外部案例"
      input_schema = {...}

      def execute(self, query: str) -> ToolResult:
          pass
  ```
- [ ] **测试先行**：`tests/unit/test_web_search.py`
  - Mock HTTP请求，测试Tavily/SerpAPI响应解析
  - 测试结果截断（≤500字）
  - 测试错误处理（API失败、超时）
- [ ] **实现**：
  - 优先集成Tavily（API简单，文档完善）
  - 配置：`TAVILY_API_KEY`环境变量
  - 结果格式化：提取标题、摘要、URL，组织为紧凑文本

**3.2 工具注册** (`src/agent/hub_spoke/tools.py`)
- [ ] 创建工具工厂函数
  ```python
  def create_tools(config: Config) -> dict[str, Tool]:
      return {
          "notebooklm": NotebookLMTool(config),
          "web_search": WebSearchTool(config),
      }
  ```
- [ ] 测试工具定义生成（转换为LLM backend格式）

**验收标准**：
- [x] WebSearchTool可成功调用Tavily API
- [x] 工具输出符合≤500字约束
- [x] 工具定义可被Anthropic/OpenAI backend正确解析

---

### **Phase 4: 执行引擎** (预计4-5天)

#### 目标
实现Executor的while循环 + 重写机制

#### 任务清单

**4.1 Executor核心循环** (`src/agent/hub_spoke/executor.py`)
- [ ] **测试先行**：`tests/integration/test_executor.py`
  - Mock所有Worker，测试状态机转换：
    ```
    planner → (miner) → orchestrator → writer → critic
                                            ↑        ↓
                                            └────(回溯)
    ```
  - 测试回溯逻辑：critic未通过时，state.next_step回到writer
  - 测试循环上限：iteration_count≥3时，标记DEGRADED_OUTPUT
  - 测试critic通过时：next_step="done"，循环退出
- [ ] **实现**：Executor类
  ```python
  class Executor:
      MAX_ITERATIONS = 3

      def run(self, state: State, workers: dict, tools: dict, backend, tracer):
          while state.next_step != "done":
              if state.next_step == "planner":
                  result = workers["planner"].run(state, backend, tracer)
                  # 更新state，决定next_step
              elif state.next_step == "miner":
                  # ... 类似逻辑
              elif state.next_step == "writer":
                  result = workers["writer"].run(state, backend, tracer)
                  state.draft = result.output
                  state.next_step = "critic"
              elif state.next_step == "critic":
                  result = workers["critic"].run(state)
                  tracer.append_critic_result(...)
                  if result.passed:
                      state.next_step = "done"
                  elif state.iteration_count >= self.MAX_ITERATIONS:
                      tracer.save_article(state.draft, degraded=True)
                      state.next_step = "done"
                  else:
                      state.critic_feedback = result.reason
                      state.iteration_count += 1
                      state.next_step = "writer"
          return state
  ```

**4.2 重写反馈注入**
- [ ] **Writer提示词扩展**：`prompts/hub-spoke/writer.txt`
  ```jinja2
  {% if critic_feedback %}
  上一轮审稿意见：{{ critic_feedback }}
  请针对以上问题修改，其余部分保持原有风格。
  {% endif %}
  ```
- [ ] **测试**：Mock critic返回不同feedback，验证writer收到正确的context

**验收标准**：
- [x] Executor可完整执行状态机转换
- [x] 重写循环≤3次，超限时正确标记降级
- [x] 每轮critic_feedback正确注入writer的system prompt

---

### **Phase 5: Worker实现** (预计5-6天)

#### 目标
适配现有Agent到新架构，实现workers/目录

#### 任务清单

**5.1 Miner双层输出** (`src/agent/hub_spoke/workers/miner.py`)
- [ ] **提示词改造**：`prompts/hub-spoke/miner.txt`
  - 明确要求输出JSON：
    ```json
    {
      "structured_points": ["观点A", "观点B"],
      "raw_voice_clips": ["原话片段1", "原话片段2"]
    }
    ```
  - 相关性筛选约束：仅返回与选题强相关的内容
  - 总体≤500字
- [ ] **测试先行**：`tests/unit/test_miner.py`
  - Mock NotebookLM返回，测试JSON解析
  - 测试structured_points和raw_voice_clips分别传递给下游
- [ ] **实现**：MinerWorker类
  ```python
  class MinerWorker:
      def run(self, state: State, backend, tool, tracer):
          # 调用NotebookLM，解析双层JSON
          # 更新state.structured_points, state.raw_voice_clips
          pass
  ```

**5.2 Orchestrator适配** (`src/agent/hub_spoke/workers/orchestrator.py`)
- [ ] **输入**：state.structured_points + state.web_research
- [ ] **输出**：紧凑大纲(≤800字)，写入state.outline
- [ ] **提示词**：在system prompt末尾加上下文裁剪约束
- [ ] **测试**：验证输出字数限制

**5.3 Writer适配** (`src/agent/hub_spoke/workers/writer.py`)
- [ ] **输入**：state.outline + state.raw_voice_clips + state.critic_feedback(可选)
- [ ] **输出**：state.draft
- [ ] **提示词**：
  - 使用raw_voice_clips的语气和措辞
  - 条件块处理critic_feedback
- [ ] **测试**：验证风格保留、定向修改

**5.4 Workers工厂** (`src/agent/hub_spoke/workers/__init__.py`)
- [ ] 实现create_workers工厂函数
  ```python
  def create_workers(config: Config) -> dict:
      return {
          "planner": PlannerWorker(),
          "miner": MinerWorker(config),
          "web": WebWorker(config),
          "orchestrator": OrchestratorWorker(),
          "writer": WriterWorker(),
          "critic": CriticWorker(),
      }
  ```

**验收标准**：
- [x] Miner双层输出格式正确
- [x] Orchestrator大纲≤800字
- [x] Writer能正确使用raw_voice_clips风格
- [x] 所有Worker集成测试通过

---

### **Phase 6: 端到端集成** (预计3-4天)

#### 目标
完整流程集成 + CLI入口 + E2E测试

#### 任务清单

**6.1 Hub-Spoke Flow主函数** (`src/agent/hub_spoke/flow.py`)
- [ ] **实现**：
  ```python
  def run_hub_spoke_flow(
      topic: str,
      user_context: str,
      config: Config,
      on_progress: Callable,
      tracer: OutputTracer,
  ) -> HubSpokeResult:
      state = State(topic=topic, user_context=user_context)
      backend = get_backend(config.llm_provider)
      tools = create_tools(config)
      workers = create_workers(config)

      executor = Executor()
      final_state = executor.run(state, workers, tools, backend, tracer)

      return HubSpokeResult(
          success=True,
          output=final_state.draft,
          degraded=(final_state.status == "DEGRADED_OUTPUT"),
      )
  ```

**6.2 CLI入口扩展** (`main.py`)
- [ ] 添加`--flow`参数：选择`insight-alignment`或`hub-spoke`
- [ ] 根据参数调用不同flow函数
- [ ] 保持向后兼容（默认为insight-alignment）

**6.3 端到端测试** (`tests/e2e/test_hub_spoke_flow.py`)
- [ ] **集成测试场景**：
  1. **纯AI写作**：user_context≥300字，Planner选择both=false
  2. **只私域调研**：use_private=true, use_web=false
  3. **全量调研**：both=true，顺序调用Miner+Web
  4. **Critic通过**：第一轮即达标，无重写
  5. **Critic重写1轮**：第一轮未过，第二轮通过
  6. **降级输出**：3轮均未过，输出DEGRADED标记
- [ ] **验证点**：
  - Trace文件包含所有Agent调用
  - article.md内容正确
  - 降级场景下文件头部有⚠️标记
  - agent_inputs.json包含所有输入记录

**6.4 文档更新**
- [ ] 更新README.md：
  - 新增Hub-Spoke架构说明
  - 使用示例：`python main.py --flow hub-spoke "如何提升个人品牌"`
  - 配置说明：TAVILY_API_KEY等新增环境变量
- [ ] 新增`doc/hub_spoke_架构实现.md`：
  - 模块结构图
  - 数据流图
  - 各Worker职责说明
  - Trace文件示例

**验收标准**：
- [x] 6种E2E场景全部通过
- [x] CLI可正常切换两种flow
- [x] 文档完整，示例可运行

---

## 三、关键文件清单

### 3.1 新增文件

```
src/agent/hub_spoke/
├── __init__.py                  # 导出HubSpokeFlow
├── state.py                     # State数据类
├── router.py                    # 路由模块（XML信号解析）
├── executor.py                  # 执行引擎（while循环+回溯）
├── flow.py                      # run_hub_spoke_flow主函数
├── workers/
│   ├── __init__.py             # create_workers工厂
│   ├── planner.py              # Planner Agent
│   ├── miner.py                # Miner Agent（双层输出）
│   ├── web.py                  # Web Agent
│   ├── orchestrator.py         # Orchestrator Agent
│   ├── writer.py               # Writer Agent
│   └── critic.py               # Critic Agent（规则检查）
└── tools.py                     # create_tools工厂

src/tools/
└── web_search.py                # WebSearchTool（Tavily/SerpAPI）

prompts/hub-spoke/
├── planner.txt                  # Planner提示词
├── miner.txt                    # Miner提示词（双层输出）
├── orchestrator.txt             # Orchestrator提示词（上下文裁剪）
└── writer.txt                   # Writer提示词（critic_feedback条件块）

tests/
├── unit/
│   ├── test_state.py
│   ├── test_router.py
│   ├── test_critic.py
│   ├── test_planner.py
│   ├── test_miner.py
│   └── test_web_search.py
├── integration/
│   ├── test_executor.py
│   └── test_workers.py
└── e2e/
    └── test_hub_spoke_flow.py

doc/
└── hub_spoke_架构实现.md        # 架构文档
```

### 3.2 修改文件

```
src/output/tracer.py             # 扩展append_critic_result, save_article(degraded)
main.py                          # 添加--flow参数，调用hub_spoke_flow
README.md                        # 新增Hub-Spoke使用说明
.env.example                     # 新增TAVILY_API_KEY示例
```

---

## 四、测试验证策略

### 4.1 单元测试覆盖率目标

| 模块 | 覆盖率目标 | 关键测试点 |
|------|-----------|-----------|
| state.py | ≥95% | 初始化、字段验证、序列化 |
| router.py | ≥90% | XML解析、降级处理、各种status |
| critic.py | 100% | 所有规则分支、评分逻辑 |
| planner.py | ≥85% | 4种路径决策、JSON解析 |
| executor.py | ≥85% | 状态转换、回溯逻辑、循环上限 |
| workers/* | ≥80% | 各Worker的输入/输出格式 |

### 4.2 集成测试场景

**Executor集成测试**（Mock所有Worker）：
1. 正常流程：planner→miner→orchestrator→writer→critic(pass)
2. 跳过私域：planner→orchestrator→writer→critic(pass)
3. 重写1轮：writer→critic(fail)→writer→critic(pass)
4. 降级输出：writer→critic(fail)×3→DEGRADED

**Worker集成测试**（Mock Backend + Real Tools）：
1. Miner调用真实NotebookLM（需测试环境配置）
2. Web调用真实Tavily（需API key）
3. 验证输出格式和字数限制

### 4.3 端到端测试

**E2E测试矩阵**（6种场景×3种backend）：

| 场景 | Backend | 验证点 |
|------|---------|--------|
| 纯AI写作 | Anthropic | Planner输出both=false |
| 全量调研 | OpenAI | Miner+Web均被调用 |
| Critic通过 | MiniMax | 无重写，trace包含1次critic |
| Critic重写1轮 | Anthropic | trace包含2次writer+2次critic |
| 降级输出 | OpenAI | article.md头部有⚠️ |
| 只私域 | Anthropic | Web未被调用 |

### 4.4 性能测试

**基准指标**（单次完整流程）：
- **总耗时**：≤5分钟（正常场景，无重写）
- **工具调用**：NotebookLM ≤5次，Web ≤3次
- **Token消耗**：≤50k tokens（含所有Agent调用）
- **Trace文件大小**：≤500KB

---

## 五、风险与降级方案

### 5.1 潜在风险

| 风险 | 概率 | 影响 | 降级方案 |
|------|------|------|----------|
| **并行调研实现复杂** | 中 | 低 | 先用顺序执行，Phase 2优化 |
| **Web工具API限流** | 中 | 中 | 添加重试+指数退避，fallback到顺序调用 |
| **Critic规则不准** | 高 | 中 | 先用宽松规则(字数≥500)，逐步调优 |
| **上下文超限** | 中 | 高 | 在每个Worker强制截断，监控token消耗 |
| **Planner决策偏差** | 中 | 中 | 在prompt中加明确示例，可人工override |

### 5.2 回滚策略

- 保留原有`insight_alignment.py`不变
- 新架构出问题时，CLI可回退到`--flow insight-alignment`
- 生产环境先用影子模式（同时运行两种flow，对比输出质量）

---

## 六、时间估算

| 阶段 | 预计时间 | 关键里程碑 |
|------|---------|-----------|
| Phase 1: 基础设施 | 2-3天 | State/Router/Tracer扩展完成 |
| Phase 2: 核心Agent | 3-4天 | Planner/Critic通过单元测试 |
| Phase 3: 工具集成 | 2-3天 | WebSearchTool可调用Tavily |
| Phase 4: 执行引擎 | 4-5天 | Executor集成测试通过 |
| Phase 5: Worker实现 | 5-6天 | 所有Worker集成测试通过 |
| Phase 6: E2E集成 | 3-4天 | 6种E2E场景全部通过 |
| **总计** | **19-25天** | 完整Hub-Spoke架构上线 |

---

## 七、成功标准

### 7.1 功能完整性
- [x] 支持4种调研路径（纯AI/只私域/只全网/全量）
- [x] Critic质量评审可正常工作（规则检查100%准确）
- [x] 重写循环≤3次，降级标记正常
- [x] 双层输出（Miner）、上下文裁剪生效

### 7.2 测试覆盖率
- [x] 单元测试覆盖率≥85%
- [x] 集成测试覆盖所有状态转换
- [x] E2E测试6种场景×3种backend全部通过

### 7.3 可观测性
- [x] Trace文件包含完整Agent调用链
- [x] 降级场景有明确标记
- [x] Critic评审结果以表格形式记录
- [x] agent_inputs.json可用于离线分析

### 7.4 文档完善
- [x] README包含使用示例
- [x] 架构文档说明数据流和模块职责
- [x] 提示词符合约束规范

---

## 八、后续优化方向

1. **并行调研优化**：asyncio.gather同时调用Miner+Web
2. **Critic升级**：从规则检查升级为LLM评审
3. **动态循环次数**：根据Critic反馈质量调整MAX_ITERATIONS
4. **更多Web工具**：支持SerpAPI、Google Custom Search
5. **A/B测试框架**：对比两种flow的输出质量
6. **缓存机制**：NotebookLM/Web结果缓存，避免重复查询
7. **流式输出**：Writer生成时实时展示进度

---

**计划制定完成，等待审核批准后开始Phase 1实施。**
