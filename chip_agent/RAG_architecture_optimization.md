# RAG 文档分类架构优化与多源检索实现计划

针对您提出的测试失败问题（STA 提问无回答）以及文档分类不够细致、跨领域汇集能力弱的痛点，我们制定了如下架构优化与修复计划。

## 1. 解决当前“提问无回答”的 Bug (Bug Fix)
**现象**：提问 "What is STA" 时，后台抛出了 `ValidationError: temperature none is not an allowed value` 的错误。
**原因**：LangGraph 的 State 中 `temperature` 键存在，但其值为 `None`。`state.get("temperature", 0.0)` 仍然返回 `None` 而不是 `0.0`，导致初始化 `ChatOpenAI` 报错。该问题在所有 Expert 节点中都可能存在。
**修复方案**：
- 全局扫描并替换：将 `state.get("temperature", 0.0)` 改为 `state.get("temperature") or 0.0`。

---

## 2. RAG 文档分类新架构 (Document Taxonomy Mapping)
我们将原来的 4 类（PDK, EDA, Project_Doc, General）扩充为 **7大专业类别**，以更细粒度地管理文档，提高检索精度。新的映射方案（Schema）如下：

| 原分类类别 | 新增/细化分类类别 (Category) | 包含的文档类型 | 对应的额外 Metadata 标签 |
|:---|:---|:---|:---|
| Project_Doc | **Project** (项目文档) | PRD, Spec, CRG图, Visio图, Word, 项目经验, PPT, Excel | `project_id`, `milestone` |
| EDA | **EDA** (工具手册) | EDA工具 Guide, 命令手册 (Command Reference) | `tool_name`, `version` |
| PDK | **PDK** (工艺与规则) | PDK文件, 不同工艺的 DRC rule, Datasheet | `process_node`, `foundry` |
| - | **IP** (IP库文档) | IP Datasheet, IP User Guide | `ip_name`, `ip_vendor` |
| - | **Training** (团队与培训) | 团建经验积累, 新人培训材料 | `topic`, `author` |
| - | **Literature** (学术与书籍) | 经验书籍（如《STA For Nanometer Designs》）, 学术论文 | `domain`, `author` |
| - | **Script** (脚本库) | TCL/Python 脚本, Makefile 经验库 | `language`, `tool_name` |

---

## 3. 跨分类信息汇集与多路检索 (Multi-category Retrieval & Aggregation)
针对“一个问题涉及不同文档分类，怎么汇集相关信息回答”的问题，我们将重构大模型的**路由节点 (Supervisor)** 与**检索节点 (Retriever)**：

### 3.1 Supervisor 路由改造
目前的 Supervisor 是单选路由（只能返回一个 Category）。我们需要修改 `src/supervisor.py` 中对大模型的结构化输出定义（Pydantic Schema）：
- **原来**：`category: str`
- **改造后**：`categories: List[str]`。大模型可以根据用户意图，输出多个类别。例如查询“STA分析方法”，Supervisor 可以同时输出 `["Literature", "EDA", "Project"]`。

### 3.2 Retriever 混合检索改造
修改底层的 Retriever (如 `src/retrieval/project_retriever.py` / `vector_store.py`)：
- 当识别到多个分类时，向向量数据库 (pgvector) 下发的 metadata 过滤条件从等于 (`==`) 改为包含 (`$in` 算子)。
- **聚合召回**：向量数据库将从多个文档集合中同时执行 KNN (K近邻) 查询，返回得分最高的 Top-K 个文档片段。这些片段天生带有不同的出处。

### 3.3 Synthesizer (信息汇总生成) 优化
将多路检索返回的 chunks 喂给最终的回答节点（Expert/Finalizer）时，在 Prompt 中强化“跨文档综合分析”的系统指令：
- 要求大模型在生成回答时，标明信息来源（例如：“根据 EDA 工具手册...，同时结合项目 PRD 文档要求...”）。

---

## 4. 验证计划 (Verification Plan)
1. 修复 temperature bug 后，使用脚本重新跑通 "What is STA" 问题。
2. 运行 `pytest` 并修复因分类变更导致的现有测试用例失败。
3. 模拟一条复杂的跨域查询（例如："用 Innovus 跑 N5 工艺的 STA 流程"），验证系统能否同时从 `EDA`、`PDK` 和 `Literature` 三个维度召回信息。
