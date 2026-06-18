# 芯片问答助手 RAG 检索问题修复总结

## 1. 解决的问题与实现要点
**问题现象**：在 Open WebUI 中，用户针对上传的《Static Timing Analysis for Nanometer Designs》文档提出专业问题时，模型未能返回基于文档的回答，而是给出通用的问候语或表示未检索到相关信息。
**实现要点**：
- **修复检索过滤逻辑**：更新 `src/retrieval/project_retriever.py`，将元数据（Metadata）的过滤机制由严格的白名单改为排除内部状态字段（如 `confidence`, `missing_fields` 等），从而实现更灵活和健壮的元数据过滤。
- **解决异步与同步的冲突**：修复了 `src/vector_store.py` 中的关键 bug。由于 `langchain-postgres` 缺乏正确的 `_async_engine` 支持导致 `asimilarity_search` 失败，采用了 `asyncio.to_thread` 将同步的 `similarity_search` 包装为异步调用。
- **完善并更新单元测试**：调整 `tests/test_project_retriever.py` 和 `tests/test_metrics_subgraph.py`，使之适配新的 `Project_Doc` 文档类别命名规则，以及 `project_id` 变为可选参数的检索逻辑。
- **集成与端到端验证**：通过 `test_active_flow.py` 验证了从问答输入到 RAG 检索的完整数据流，并在 8080 端口验证了服务正常返回。最终确保项目中 211 个单元测试全部通过。

## 2. 解决问题的思路与原因
1. **排查检索链路**：文档已经成功入库并建立了向量索引，但问答时却无法命中。分析请求后发现，带有 AgentState 内部变量的请求被直接传递给了向量数据库进行精准过滤匹配，导致过滤条件过严（包含无关字段），从而检索不到数据。
2. **元数据污染（Metadata Pollution）原因**：在之前的实现中，Agent 状态字典中的一些内部决策键值（如置信度 `confidence` 等）被意外引入到了向向量库发出的查询条件中。因此思路是：不修改原有业务字段，而是在组装查询过滤器时主动剔除这些不属于文档 Schema 的系统字段。
3. **数据库异步驱动报错分析**：在进行向量检索时报错 `_async_engine not found`。原因是底层的 PostgreSQL 驱动目前使用的是同步连接池，无法直接使用原生异步方法。考虑到更换底层驱动成本较高且容易引发连锁反应，采用了 `asyncio.to_thread` 将同步阻塞方法放入线程池执行，以兼顾异步服务的并发能力和底层组件的稳定性。

## 3. 涉及的技术栈说明
- **LangGraph**：作为整体 Agent 的编排器。系统内由 `MetricsAnalyst` 节点管理 `MetricsSubgraph`，利用 LangGraph 的状态机特性，将用户请求路由至 SQL 执行（针对结构化数据）或基于文档的 RAG 检索（针对非结构化数据）。
- **langchain-postgres / pgvector**：底层的向量数据库及检索框架，支持向量相似度计算及基于 JSONB 的 Metadata 混合查询。
- **FastAPI & Uvicorn**：用于提供模型服务（如 `chip_agent`）。作为 HTTP 后端框架承接 WebUI 发来的标准 API 请求并流式返回给前端。
- **asyncio (Python 标准库)**：通过 `asyncio.to_thread` 处理同步的数据库调用，避免阻塞 FastAPI 的事件循环（Event Loop）。

## 4. 可用保留的经验与最佳实践
1. **防御性设计（防元数据污染）**：在 RAG 框架中，状态管理（Agent State）和持久化层（Vector DB Metadata）必须严格隔离。向数据库发送过滤条件时，务必只包含被明确定义的 Schema 字段（通过白名单），或者强制剔除系统内部字段（黑名单）。
2. **异步服务中的阻塞调用处理**：在使用 Python 的异步框架时，一旦遇到依赖库不支持异步方法（如本例中部分 langchain 底层组件），优先使用 `asyncio.to_thread`（或者 ThreadPoolExecutor）将阻塞操作委托给子线程，不要强行修改底层库的连接方式，这样既能解决报错，又不会破坏现有的组件依赖。
3. **服务热更新与持久化**：由于容器化或特定部署环境下，Uvicorn 启动的服务不会自动热加载代码变更（特别是未使用 `--reload` 或在后台进程中运行时），因此每次修改核心业务逻辑或图节点逻辑后，**必须手动重启后台模型服务**以使得代码生效。
