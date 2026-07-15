# RAG 模块无返回数据问题修复计划

当测试 "what is sta" 等通用知识/文献类问题时，RAG 系统返回 "No matching data..."，表明检索模块未能获取到有效的文档片段。

完整的实施方案已经直接输出至项目工作区，请点击下方链接直接在编辑器中阅读：

> [!IMPORTANT]
> **工作区详细方案路径**：[2026-07-07-rag-bugfix-plan.md](file:///home/eason/proj/open-webui/docs/superpowers/plans/2026-07-07-rag-bugfix-plan.md)

---

## 方案概要

### 1. 根本原因
* 通用概念问题（如 STA）被 Supervisor 正确归入 `Literature` 类别，并路由至 `metrics_analyst`。
* `metrics_subgraph.py` 的 `retrieve_docs_node` 之前被硬编码为仅通过 `project_retriever` 在 `project_docs` 集合中检索。
* 但 `project_docs` 集合仅有 4 个项目特定 specs 块，不含任何时序分析通用文档。而多达 14 万块的 Cadence Innovus 官方手册则存储在 `eda_manuals` 集合中。
* 此外，`categories: ["Literature"]` 过滤器与 `eda_manuals` 中的 `EDA` 标签不匹配，导致即使跨集合查询也会被元数据过滤为 0 结果。

### 2. 修复逻辑
* **多集合动态分发**：根据 Supervisor 预测的元数据分类，动态分发至 `pdk_rules`、`eda_manuals` 和 `project_docs` 集合中执行检索。例如，`Literature` 会同时并发检索 `project_docs` 与 `eda_manuals` 集合。
* **元数据类别匹配清洗**：在分发时拷贝并过滤 categories 参数，确保调用各 collection 的检索器时不会因为类别过滤器不匹配而产生 0 结果。
* **合并与精排**：使用 asyncio 并行检索，将多集合返回的候选 chunks 合并后根据 Reranker 评分倒序排列，取 Top-K 最佳 chunks 送入 LLM 总结。

---

## 拟修改的文件规划

### [MODIFY] [metrics_subgraph.py](file:///home/eason/proj/open-webui/jbprag/src/experts/metrics_subgraph.py)
* 重构 `retrieve_docs_node` 函数，实现并行分发与合并重新精排的逻辑。

---

## 验证计划

1. **测试脚本验证**：运行 `scratch/test_dispatcher.py` 验证 "What is STA" 能跨集合从 `eda_manuals` 召回正确的 Timing 相关 chunks。
2. **手动作业联调**：在 Open WebUI 聊天框中提问 "what is sta"，确认能成功返回参考 Cadence 手册 hometown 时序定义和引用的角标。
