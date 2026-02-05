# 提示词目录说明

所有提示词均放在此目录，**不写在代码中**，便于维护与迭代。

**当前只保留一套流程：洞察对齐**，对应 `prompts/insight-alignment/` 下各文件。

---

## 目录结构

```
prompts/
├── README.md                    # 本说明
├── prompt_run.txt               # [已不用] 原单流程提示词，仅作参考保留
│
└── insight-alignment/           # 当前唯一流程：洞察对齐
    ├── insight_specialist.txt   # 洞察顾问：选题 → 写作建议 + 核心洞察 + 缺口清单
    ├── orchestrator.txt         # 总编辑：选题 + 洞察回复 → 派单（私域挖掘 / 直接合成）
    ├── knowledge_miner.txt      # 私域挖掘员：按缺口在 NotebookLM 深挖
    ├── web_researcher.txt       # 全网调研员：靶向搜索（工具未实现时作占位）
    └── ghostwriter.txt          # 风格执笔人：洞察 + 挖掘结果 → 最终文章
```

---

## 流程与调用顺序（洞察对齐）

1. **洞察顾问**（`insight_specialist.txt`）  
   用户发选题 → 调用 NotebookLM → 输出：写作建议、核心洞察、缺口清单。

2. **总编辑**（`orchestrator.txt`）  
   输入：用户选题 + 洞察顾问回复。  
   输出：派单决策（「派单私域挖掘员」+ 查询列表，或「直接合成」）。

3. **私域挖掘员**（`knowledge_miner.txt`）  
   仅当总编辑派单时执行：按查询列表调用 NotebookLM，汇总私域细节。

4. **全网调研员**（`web_researcher.txt`）  
   占位；工具未实现前不参与流程。

5. **风格执笔人**（`ghostwriter.txt`）  
   输入：选题 + 洞察顾问输出 + 私域挖掘结果。  
   输出：最终公众号正文 + 标题。

**入口**：`python main.py "选题"`，固定走上述流程。

---

## 加载方式

- 子目录：`load_prompt("insight-alignment/insight_specialist.txt")` → `prompts/insight-alignment/insight_specialist.txt`
- 其他：`load_prompt("xxx.txt")` → `prompts/xxx.txt`
