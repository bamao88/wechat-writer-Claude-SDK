# Hub-Spoke 架构问题记录

## 已解决问题

### Issue #1: 日志不完整（✅ 已修复）

**问题描述**
- `thought_trace.md` 在 Critic 结果处被截断，缺少执行摘要和最终完成标记
- tracer 没有调用 close()，导致摘要占位符未被替换，agent_inputs.json 未保存

**根本原因**
- `executor.run()` 和 `run_hub_spoke_flow()` 异常处理中都没有调用 `tracer.close()`
- 即使正常完成，executor 也没有显式调用 close()

**解决方案**（已实施）
1. executor.py 第 114-119 行：主流程结束时添加 `tracer.close()`
2. flow.py 异常处理：添加 `tracer.close()` 确保异常时也关闭
3. executor.py 第 114 行：添加"🏁 执行完成"标记到日志

**验证方法**
```bash
tail thought_trace.md
# 应该看到：
# ## 🏁 执行完成
# **状态**: COMPLETED
# **最终评分**: X/10
```

---

### Issue #2: Critic 评分标准矛盾（⚠️ 部分修复，需进一步验证）

**问题描述**
- Critic 评分 7 分时标记"通过"，但同时说"论点缺失严重"
- 使用 Writer 重写无法解决资料不足的问题

**当前状态**
- `PASS_SCORE_THRESHOLD` 从 7 改为 8（已实施）
- 但这只是缓解，不是根本解决

**已实施改动**
```python
# critic.py 第 20-22 行
PASS_SCORE_THRESHOLD = 8  # 提高通过线
```

**效果**
- 论点缺失 ≥50%：扣3分 → 评分7 → 不通过 → 触发重写（最多3轮）
- 但论点缺失是资料问题，Writer 重写无法根本解决

---

## 待解决问题（架构级）

### Issue #3: Critic 诊断信息不足 ⏸️

**问题描述**
```
当前：Critic 只返回 boolean (passed)
期望：Critic 返回结构化诊断信息
```

Critic 无法区分失败原因：
- 字数不足 → Writer 需要扩写
- 结构不完整 → Orchestrator 需要重新编排
- **论点缺失** → **Miner/Web 需要重新调研**（但当前架构不支持）

**影响**
- Executor 无法做出针对性修复
- 所有失败都让 Writer 重写，不合理

**解决思路**
CriticResult 应包含：
```python
@dataclass
class CriticResult:
    score: int
    passed: bool
    issues: Dict[str, bool] = {
        'word_count': False,
        'structure': False,
        'outline_alignment': False,
        'outline_completeness': False,
    }
    suggested_action: str  # 'rewrite' | 'research' | 'replan'
```

**相关代码文件**
- `src/agent/hub_spoke/workers/critic.py` - Critic 检查逻辑
- `src/agent/hub_spoke/executor.py` - 路由决策逻辑

---

### Issue #4: 论点判断方法过于粗暴 ⏸️

**问题描述**
```python
# critic.py line 182
if point not in draft:  # 只是字符串匹配！
    missing_points.append(point)
```

无法检测：
- 同义表达（"上下文隔离" vs "信息断层"）
- 论点是否被充分论述（可能只提了一句）
- 论点是否在正确的逻辑位置

**改进方向**
- 使用语义相似度匹配（而不是字符串匹配）
- 检查论点周围的上下文（是否充分论述）
- 可能需要 LLM 辅助判断（但会增加 token 成本）

---

### Issue #5: 架构流程不支持增量调研 ⏸️

**问题描述**
- Miner/Web 只在流程开始调研一次
- 如果 Critic 检测到资料不足，无法触发"增量调研"
- 当前只能让 Writer 在现有资料基础上重写

**设计缺陷**
```
当前流程：Planner → Miner/Web → Orchestrator → Writer → Critic → (如果失败) Writer重写
期望流程：Planner → Miner/Web → Orchestrator → Writer → Critic
         → (如果论点缺失) Orchestrator重新编排或触发增量调研
         → (如果字数不足) Writer扩写
         → (如果结构差) Orchestrator重建
```

**解决思路**（待讨论）
A) 让 Critic 返回诊断信息，Executor 做针对性路由
B) 在 Orchestrator 后添加"大纲完整度校验"，提前发现问题
C) 实现一个"增量调研"的 Agent，补充缺失的论点

---

## 日志输出验证清单

每次运行后检查 `thought_trace.md`：

- [ ] 开头有"📊 执行摘要"（包含 mermaid 图和表格）
- [ ] Agent 调用链完整（Planner → Miner → Web → Orchestrator → Writer → Critic）
- [ ] 每个 Agent 都有 Input 和 Output
- [ ] Critic Result 记录了评分和通过状态
- [ ] 末尾有"🏁 执行完成"标记
- [ ] 文件行数合理（不被截断）

验证命令：
```bash
wc -l thought_trace.md
tail -20 thought_trace.md
grep "🏁 执行完成" thought_trace.md
```

---

## 文件修改历史

| 文件 | 修改内容 | 日期 |
|------|---------|------|
| `executor.py` | 添加 tracer.close() 和完成标记 | 2026-03-03 |
| `flow.py` | 异常处理中添加 tracer.close() | 2026-03-03 |
| `critic.py` | PASS_SCORE_THRESHOLD 改为 8 | 2026-03-03 |

---

## 下一步行动

1. **立即验证**：用新代码运行一个完整流程，检查日志是否完整
2. **短期**：如果日志还有问题，调试 tracer.close() 的执行路径
3. **中期**：改进 Critic 的诊断信息结构（Issue #3）
4. **长期**：重新设计 Executor 的路由逻辑，支持增量调研

