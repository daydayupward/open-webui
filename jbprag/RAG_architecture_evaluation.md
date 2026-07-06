# 目前 Chip RAG 的实现现状与架构评估

基于 `jbprag/src` 和相关架构设计文档的代码核对，以下是当前 Chip RAG 的实现现状、与 SOTA 方案的对比、不足及优化方向总结，以及当前的 Router 架构图。

## 一、 目前 Chip RAG 的实现与 Router 架构图

目前的实现主要依托 **LangGraph** 构建了一个基于多路分支（Multi-Agent Routing）的架构，属于**进阶 RAG (Advanced RAG)** 中非常典型的 **Router/Dispatcher** 模式。

### 1. Router 架构图

```mermaid
graph TD
    UserQuery([用户输入查询]) --> Supervisor[Supervisor Node<br/>(LLM意图识别 & 结构化JSON提取)]
    
    subgraph Metadata Extraction
        Supervisor -.-> Meta(提取: Category, Node, Tool, Project_ID)
    end
    
    Supervisor --"route=PDK"--> PDK[PDK Expert Node]
    Supervisor --"route=EDA"--> EDA[EDA Script Expert Node]
    Supervisor --"route=METRICS"--> Metrics[Metrics Analyst Node]
    Supervisor --"route=FINALIZER<br/>(无明确意图)"--> Finalizer(Finalizer Node)

    subgraph RAG Retrieval & Generation
        PDK --> |1. 携带Meta执行| PDK_Ret[(PDK 向量库检索)]
        PDK_Ret --> |2. 拼接上下文| PDK_LLM{LLM 答案生成}
        
        EDA --> |1. 携带Meta执行| EDA_Ret[(EDA 向量库/代码库检索)]
        EDA_Ret --> |2. 拼接上下文| EDA_LLM{LLM 答案生成}
        
        Metrics --> |1. 携带Meta执行| Met_Ret[(Metrics 数据/SQL检索)]
        Met_Ret --> |2. 拼接上下文| Met_LLM{LLM 答案生成}
    end

    PDK_LLM --> Finalizer
    EDA_LLM --> Finalizer
    Met_LLM --> Finalizer

    Finalizer --> Output([组装上下文与工具日志<br>输出最终回答])
```

### 2. 实现核心逻辑
- **Supervisor (大模型路由层)**: 收到问题后，强制 LLM 输出 JSON 格式，不仅决定下一步走向（PDK / EDA / METRICS / FINISH），还扮演了 **Query Constructor (查询构造器)** 的角色，将用户的自然语言提取出 `node` (工艺节点), `tool` (EDA工具), `project_id` (项目号) 等元数据。
- **Expert Nodes (专家执行层)**: 不同的路由分支执行特定的检索逻辑。例如 `pdk_expert_node` 会将 Supervisor 提取的元数据作为 Filter 传入 `aretrieve_pdk_rules`，获取精准 Chunk 后，利用单独配置的 System Prompt (`PDK_SYSTEM_PROMPT`) 进行答案生成。

---

## 二、 当前实现的亮点总结

1. **Self-Query Retriever 模式落地**: Supervisor 不仅做意图分类，还进行 Metadata 提取（`project_id`, `tool`, `node` 等），完美契合了高级 RAG 中将“语义检索”与“结构化过滤”结合的 SOTA 实践。这对于芯片设计中极易混淆的不同工艺节点（如 TSMC N7 与 N5 的规则差异）至关重要。
2. **多专家解耦 (MoE in RAG)**: PDK、EDA 脚本、PPA Metrics 属于完全不同的知识领域。通过独立拆分 Expert Nodes，后续可以为 EDA 添加代码解释器的 Prompt，为 Metrics 添加 Text-to-SQL 逻辑，互不干扰。
3. **前瞻的多模态集成规划**: 根据规划，系统已在着手解决芯片 DRC 报错场景的“截图 RAG”痛点，将 OCR 与视觉语义模型作为前置翻译层，这是目前垂直工业领域极具创新性的亮点。
4. **状态隔离可追溯**: 通过 LangGraph 的 `AgentState` 携带 `tool_logs` 和 `retrieved_docs`，便于前端界面（如 Open-WebUI）展示溯源引用（Citation）。

---

## 三、 是否符合 Agentic RAG / Enhance RAG 的 SOTA？

目前的实现达到了 **Advanced RAG** 的优秀水平（涵盖了 Query Routing 和 Metadata Filtering），但**距离真正的 SOTA Agentic RAG（如 CRAG, Self-RAG, 多步 ReAct）还有一定差距**。

当前的流向是**静态单向的流水线**（Pipeline：路由 -> 检索 -> 生成 -> 结束），而 SOTA Agentic RAG 的核心特征是**包含反思 (Reflection)、纠错 (Correction) 和迭代循环 (Iterative Loop)**。

### 当前存在的不足与优化方向：

| 不足之处 (Shortcomings) | 优化方向 (Optimization for Agentic RAG) |
| :--- | :--- |
| **单次检索 (One-shot Retrieval)**<br>若问题需跨文档推理（如：“查找 M2 间距规则并写一个检查它的 Tcl 脚本”），目前只能命中单一路线或检索效果不佳。 | **多步检索与工具调用 (Multi-hop & Tool-use)**<br>将 Expert 升级为真正的 ReAct Agent，允许 Expert 自己调用 `search_vector_db`。若第一次检索不到，Agent 可自我思考并改写 Query 进行二次检索。 |
| **无结果评估反馈机制 (No Reflection/Critique)**<br>无论向量库召回 Chunk 是否解决了问题，都会直接喂给 LLM 生成答案，极易在无相关文档时产生幻觉。 | **引入 CRAG (Corrective RAG) 循环**<br>在检索后增加 `Grade_Documents` 节点对召回内容打分。如果全无关，触发 `Rewrite_Query` 节点重写问题再次检索，或触发外部 `Web_Search` 工具。 |
| **缺乏答案防幻觉卡口 (Lack of Answer Grading)**<br>生成后的文本直接返回，无法保证输出的规则参数确实来源于文档，这对芯片设计是致命危险的。 | **引入 Self-RAG 生成校验**<br>在 Finalizer 之前加入校验逻辑，检查 LLM 输出是否包含引用标签 `[1]`，以及生成的事实是否与检索到的 Chunk 冲突。若冲突则重写。 |
| **仅依赖稠密向量 (Dense Vector Limitations)**<br>芯片设计有强拓扑关系（如 Cell -> Pin -> Via -> Metal Layer），单纯依靠 bge-m3 等稠密向量很难跨越层级关系。 | **引入 GraphRAG (知识图谱 RAG)**<br>探索在 Ingestion 阶段抽取实体图谱，在检索阶段利用 Graph 捕捉实体连通关系，这对于芯片 Netlist 或层次化物理规则更为有效。 |

### 总结建议
目前的实现基础（LangGraph）非常扎实。为了达到真正的 Agentic SOTA，建议您在 `graph.py` 中增加**循环边 (Conditional Edges for Loop)**，比如在 Expert 和 Finalizer 之间加入**质量评估器 (Grader)**，使得处理流程从现在的 `A -> B -> C` 转变为 `A -> B -> 判断 -> (若不行则重写检索) -> 再次 B -> C` 的自主代理模式。
