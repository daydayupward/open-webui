# RAG 模块无返回数据问题修复计划

## 问题现象与根本原因分析

### 1. 现象
当测试 "what is sta" 等通用知识/文献类问题时，RAG 系统返回 "No matching data..."，表明检索模块未能获取到有效的文档片段。

### 2. 根本原因
* **Supervisor 路由选择**：针对 "what is sta" 这种通用原理/文献型问题，分类器（Supervisor）会将其正确划分为 `Literature` 类别，并路由至通用指标子图 `metrics_analyst`。
* **检索范围受限**：在 `metrics_subgraph.py` 的文档检索节点 `retrieve_docs_node` 中，系统只调用了 `aretrieve_project_docs` 这一种检索器。
* **Collection 隔离**：`aretrieve_project_docs` 仅在 `project_docs` 向量库集合中检索。然而：
  * 项目文档集合 `project_docs` 仅包含 4 个具体的项目 Spec Chunks。
  * 通用的 EDA 使用手册（如 Innovus TCR/UG 等多达 14 万的 Chunks）存储在 `eda_manuals` 集合中。
* **元数据过滤冲突**：当分类器输出 `categories: ["Literature"]` 时，即使扩展了过滤范围，检索器也是在 `project_docs` 集合中检索 category 匹配 `Literature` 的块。由于该集合不包含任何文献数据，因此检索结果彻底为空。

---

## 🛠 修复与改进方案

### 阶段一：动态多集合分发与合并检索 (Dynamic Collection Dispatcher)
在 `metrics_subgraph.py` 的 `retrieve_docs_node` 中，不再硬编码仅调用项目检索器。改为根据 Supervisor 提取出的 `categories`，动态路由至匹配的底层向量库集合：
* `PDK`/`StdCell`/`SRAM` $\rightarrow$ 检索 `pdk_rules` 集合。
* `EDA`/`Script` $\rightarrow$ 检索 `eda_manuals` 集合。
* `Project_Doc`/`Platform_Flow`/`IP`/`General` $\rightarrow$ 检索 `project_docs` 集合。
* `Literature` $\rightarrow$ **同时检索** `project_docs` 与 `eda_manuals`（因为通用时序/设计原理通常可在工具手册和文献中找到匹配）。
* 如果为空 $\rightarrow$ **检索所有集合**。

### 阶段二：检索参数与元数据清洗
在并行调用各自检索器前，对传入的 `metadata` 进行拷贝并根据检索器限制过滤 `categories`。例如，调用 `eda_retriever` 时，清洗掉 `Literature` 标签，使其正确回退到默认的 `EDA` 标签匹配，避免因分类过滤条件不匹配导致结果为空。

---

## 拟修改的文件规划

### [MODIFY] [metrics_subgraph.py](file:///home/eason/proj/open-webui/jbprag/src/experts/metrics_subgraph.py)
* 重构 `retrieve_docs_node` 节点函数，引入并行分发、多源合并、基于 Reranker 评分排序并取 Top-K 的架构。

---

## 验证计划

### 1. 自动化单元测试
* 编写测试脚本验证 `retrieve_docs_node` 执行通用问题 "what is sta" 能否跨集合成功召回 Innovus 里的 Timing 相关 Chunks。

### 2. 手动与界面联调
* 重新在 Open WebUI 中输入 "what is sta"，验证助手是否能给出关于 STA 的定义和参考来源。
