# Jbpragic RAG 执行计划

## 1. 背景与目标

本文档基于 [设计稿](</home/eason/proj/open-webui/docs/superpowers/specs/2026-06-10-jbprag-design.md>) 与当前 `jbprag/` 代码现状整理，目标不是继续描述 MVP 已完成内容，而是给出下一阶段可以直接执行的落地计划。

当前已具备的基础能力：
- FastAPI OpenAI 兼容接口骨架：`/v1/models`、`/v1/chat/completions`
- LangGraph Supervisor 路由骨架
- `pdk_expert` 的 pgvector 检索 MVP
- `eda_script_expert` / `metrics_analyst` 的 prompt 包装节点
- 一组基础单元测试

当前与 spec 的主要差距：
- 无 streaming
- 无多轮上下文
- 无结构化 metadata 抽取和硬过滤
- 无 reranker 接入，方案已确定为 `qwen3-reranker-8b`
- `EDA Script Expert` 不是 agentic loop
- `Metrics Analyst` 未接入 SQL/指标库
- 无 ingestion / indexing 基建

### 已确认前置决策

- `langchain` / `langgraph` 以及相关生态包先升级到实施当时的最新兼容稳定版，再进入主功能开发。
- reranker 固定试用 `env.model.md` 中定义的 `qwen3-reranker-8b`，但模型名、base URL、api key 不写死在代码里，统一经配置层注入。
- 向量数据库和 metrics 数据库当前阶段先使用本地自建测试数据和种子脚本完成开发验证，后续迁移到实际工作环境时再做对接。

## 2. 执行原则

- 先补运行时底座，再做专家能力深化，避免反复返工。
- 所有 expert 都通过统一 `AgentState`、统一 retrieval / tool log 抽象接入。
- 所有检索都先做 metadata hard filter，再做向量检索和 rerank。
- 所有新增能力必须有对应单测或契约测试，不接受只靠手工 smoke test。
- 模型和服务地址从配置层读取，仓库内只保留占位配置和示例，不提交敏感凭据。

## 3. 里程碑总览

| 里程碑 | 目标 | 优先级 | 依赖 |
| --- | --- | --- | --- |
| M0 | 依赖升级与本地测试数据基线 | P0 | 无 |
| M1 | 运行时骨架重构：多轮上下文、统一 state、响应适配层 | P0 | M0 |
| M2 | Supervisor 结构化路由 + Metadata 抽取 | P0 | M0, M1 |
| M3 | PDK Expert 检索链路升级：metadata filter + reranker + 降级 | P0 | M0, M1, M2 |
| M4 | OpenAI 兼容 streaming 和事件流 | P1 | M0, M1, M2 |
| M5 | EDA Script Expert 升级为 agentic loop | P1 | M0, M1, M2, M4 |
| M6 | Metrics Analyst 升级为 RAG + Text-to-SQL | P1 | M0, M1, M2, M4 |
| M7 | Ingestion / indexing 基建 | P2 | M0, M2, M3 |
| M8 | 集成加固与验收 | P0 | M0-M7 |

建议执行顺序：
1. M0
2. M1
3. M2
4. M3
5. M4
6. M5
7. M6
8. M7
9. M8

## 4. 里程碑执行明细

### M0. 依赖升级与本地测试数据基线

**目标**
- 升级当前 `langchain` / `langgraph` 及相关依赖到最新兼容稳定版。
- 建立统一配置层，接管 LLM、embedding、reranker 模型配置。
- 先创建本地开发用向量库和 metrics 测试数据，避免阻塞后续开发。

**涉及文件**

修改：
- `jbprag/requirements.txt`
- `jbprag/src/utils.py`

新增：
- `jbprag/src/settings.py`
- `jbprag/scripts/seed_dev_data.py`
- `jbprag/dev_data/README.md`
- `jbprag/dev_data/pdk_rules.jsonl`
- `jbprag/dev_data/eda_manuals.jsonl`
- `jbprag/dev_data/project_docs.jsonl`
- `jbprag/dev_data/metrics_seed.sql`

测试：
- `jbprag/tests/test_settings.py`
- `jbprag/tests/test_dev_seed_data.py`
- `jbprag/tests/test_dependency_smoke.py`

**文件级任务**

`jbprag/requirements.txt`
- 升级 `langchain`、`langgraph`、`langchain-openai`、`langchain-postgres` 等配套包
- 锁定一组彼此兼容的版本，避免只升级单包导致 API 断裂

`jbprag/src/settings.py`
- 统一封装配置读取
- 定义 `LLM_MODEL`、`EMBEDDING_MODEL`、`RERANK_MODEL`
- 定义 `OPENAI_API_BASE_URL`、`OPENAI_API_KEY`
- 定义 `RERANK_API_BASE_URL`、`RERANK_API_KEY`
- 默认将 reranker 模型名设为 `qwen3-reranker-8b`

`jbprag/src/utils.py`
- 改为依赖 `settings.py`
- 清理当前直接散落在函数里的环境变量读取逻辑
- 为后续 `get_reranker_client()` 预留入口

`jbprag/dev_data/README.md`
- 说明本地测试数据用途、字段约定、导入方式
- 明确这些数据只用于开发验证，不代表工作环境真实结构

`jbprag/dev_data/pdk_rules.jsonl`
- 准备最小 PDK 样例
- 至少覆盖 `N5`、`N7`、多层金属 pitch、DRC/LVS 条目

`jbprag/dev_data/eda_manuals.jsonl`
- 准备 Innovus / ICC2 的最小命令文档样例

`jbprag/dev_data/project_docs.jsonl`
- 准备 `Proj_A` / `Proj_B` 项目文档样例

`jbprag/dev_data/metrics_seed.sql`
- 创建本地 metrics schema、view、样例数据
- 至少覆盖 timing、power、area 和多项目场景

`jbprag/scripts/seed_dev_data.py`
- 提供一键初始化本地 pgvector 与 metrics 数据的脚本
- 支持 `--vector-only`、`--metrics-only`、`--reset` 这类最小参数

`jbprag/tests/test_settings.py`
- 覆盖配置默认值和环境变量覆盖
- 确认 reranker 默认模型为 `qwen3-reranker-8b`

`jbprag/tests/test_dev_seed_data.py`
- 验证样例数据结构完整
- 验证 metadata 字段齐全

`jbprag/tests/test_dependency_smoke.py`
- 只做 import / API 烟测，确保升级后的核心依赖可以正常初始化

**退出标准**
- 核心依赖升级完成且现有测试可迁移
- `LLM` / `embedding` / `reranker` 统一从配置层读取
- 本地可重复初始化向量库和 metrics 测试数据

---

### M1. 运行时骨架重构

**目标**
- 支持完整对话历史进入 graph。
- 建立稳定的 `AgentState` 和 transport 适配层。
- 为后续 streaming、tool logs、metadata、子图扩展打底。

**涉及文件**

修改：
- `jbprag/src/main.py`
- `jbprag/src/graph.py`

新增：
- `jbprag/src/state.py`
- `jbprag/src/api_models.py`
- `jbprag/src/message_utils.py`
- `jbprag/src/response_formatter.py`

测试：
- `jbprag/tests/test_api.py`
- `jbprag/tests/test_graph.py`
- `jbprag/tests/test_message_utils.py`

**文件级任务**

`jbprag/src/state.py`
- 定义统一 `AgentState`
- 至少包含：`messages`、`route`、`metadata`、`retrieved_docs`、`tool_logs`、`final_answer`、`errors`、`request_id`
- 为 list 类型字段设置 LangGraph 可累加语义

`jbprag/src/api_models.py`
- 定义 `ChatRequest`、`ChatMessage`、`ChatCompletionResponse`
- 预留 `stream`、`metadata`、`temperature` 等兼容字段
- 对齐 OpenAI 请求格式的最小必要字段

`jbprag/src/message_utils.py`
- 新增 OpenAI message -> LangChain message 的转换逻辑
- 保留历史 `system` / `user` / `assistant` 角色
- 统一提取最后一轮 user turn，但不丢弃历史

`jbprag/src/response_formatter.py`
- 将 graph 输出统一格式化为 OpenAI `chat.completion`
- 为后续 chunk / SSE 输出预留 formatter

`jbprag/src/graph.py`
- 引入新的 `AgentState`
- 取消当前“expert 执行完再回 supervisor 判断 FINISH”的双跳结构
- 先重构为：`supervisor -> selected expert -> finalizer -> END`
- finalizer 负责组装 `final_answer` 与 trace

`jbprag/src/main.py`
- 改为调用 message normalizer 和 response formatter
- 全量传递会话消息，不再只取最后一条
- 增加 request id

`jbprag/tests/test_message_utils.py`
- 覆盖多轮消息转换
- 覆盖 `system + user + assistant + user` 顺序

`jbprag/tests/test_api.py`
- 覆盖多轮请求
- 确认 response 仍兼容当前 OpenAI 风格结构

`jbprag/tests/test_graph.py`
- 验证新图结构只路由一次 supervisor
- 验证 finalizer 会输出最终答复

**退出标准**
- 非流式请求可携带完整对话历史
- graph 输出中包含结构化 `final_answer`
- 现有测试迁移后通过

---

### M2. Supervisor 结构化路由与 Metadata 抽取

**目标**
- Supervisor 不只做意图分类，还要输出结构化 metadata。
- 为 PDK / EDA / Metrics 的硬过滤和追问逻辑提供统一输入。

**涉及文件**

修改：
- `jbprag/src/graph.py`
- `jbprag/src/utils.py`

新增：
- `jbprag/src/supervisor.py`
- `jbprag/src/prompts/supervisor_prompt.py`
- `jbprag/src/metadata.py`

测试：
- `jbprag/tests/test_supervisor.py`
- `jbprag/tests/test_graph.py`

**文件级任务**

`jbprag/src/metadata.py`
- 定义 metadata schema
- 至少包含：`category`、`node`、`tool`、`project_id`、`confidence`、`missing_fields`
- 增加标准化函数，将 `n5` 归一化为 `N5` 这类值

`jbprag/src/prompts/supervisor_prompt.py`
- 把当前写死在 `graph.py` 里的 prompt 独立出来
- 明确要求输出结构化 JSON
- 明确合法枚举值和缺失字段处理策略

`jbprag/src/supervisor.py`
- 封装 supervisor 调用
- 负责 LLM 输出解析、校验、默认值和异常降级
- 产出 `route + metadata + tool_logs`

`jbprag/src/graph.py`
- 使用 `supervisor.py`
- 将 supervisor 结果写入 state
- 依据 `route` 进入对应 expert

`jbprag/src/utils.py`
- 可选：增加结构化输出模型或 JSON parser 的公共辅助逻辑

`jbprag/tests/test_supervisor.py`
- 覆盖三类典型问题：
  - PDK：`What is N5 M3 pitch?`
  - EDA：`Write an Innovus Tcl snippet to create floorplan`
  - Metrics：`Summarize timing/power history for Proj_A`
- 覆盖 metadata 缺失场景，如 project_id 缺失
- 覆盖 LLM 返回非法 JSON 的降级逻辑

**退出标准**
- supervisor 返回稳定的 `route + metadata`
- 至少能正确抽取 `node/tool/project_id` 中的已知字段
- 非法 JSON 或空响应时有确定性的回退路径

---

### M3. PDK Expert 检索链路升级

**目标**
- 让 PDK expert 真正对齐 spec：metadata hard filter -> vector search -> rerank -> summarize。
- 补齐数据库异常时的可控降级。

**涉及文件**

修改：
- `jbprag/src/vector_store.py`
- `jbprag/src/experts/pdk_expert.py`
- `jbprag/src/settings.py`

新增：
- `jbprag/src/retrieval/types.py`
- `jbprag/src/retrieval/pdk_retriever.py`
- `jbprag/src/retrieval/reranker.py`
- `jbprag/src/prompts/pdk_prompt.py`

测试：
- `jbprag/tests/test_vector_store.py`
- `jbprag/tests/test_pdk_expert.py`
- `jbprag/tests/test_pdk_retriever.py`

**文件级任务**

`jbprag/src/retrieval/types.py`
- 定义 `RetrievalRequest`、`RetrievalResult`、`RetrievedChunk`
- 明确 metadata filter、fetch_k、top_k、rerank score 的字段

`jbprag/src/vector_store.py`
- 增加支持 metadata filter 的查询入口
- 保留当前 `get_vector_store()`，但新增高层 query 函数，避免 expert 直接操作底层 PGVector
- 明确异常类型并做统一包装

`jbprag/src/retrieval/reranker.py`
- 定义 `Reranker` 抽象
- 第一版就实现 `QwenRerankerClient`
- 默认模型使用 `qwen3-reranker-8b`
- 保留 `IdentityReranker` 作为本地离线兜底和单测替身

`jbprag/src/settings.py`
- 增加 reranker 专用配置读取
- 区分通用 LLM 接口和 reranker 接口地址，避免后续服务拆分时返工

`jbprag/src/retrieval/pdk_retriever.py`
- 实现完整的 PDK 检索流水线
- 输入 supervisor 提供的 `node/category` 等 metadata
- 输出 top chunks 与检索日志

`jbprag/src/prompts/pdk_prompt.py`
- 独立 PDK system prompt
- 强调“只基于 PDK 上下文回答；不够就明确说不确定”

`jbprag/src/experts/pdk_expert.py`
- 不再自己创建 embeddings / vector store / prompt
- 改为依赖 `pdk_retriever`
- 将检索结果和异常信息写入 `tool_logs`

`jbprag/tests/test_pdk_retriever.py`
- 覆盖 metadata filter 是否生效
- 覆盖 reranker 接口是否被调用
- 覆盖 `qwen3-reranker-8b` 配置注入路径
- 覆盖空结果与 DB 异常降级

`jbprag/tests/test_pdk_expert.py`
- 覆盖“命中上下文”和“未命中上下文”两类路径
- 覆盖 `node` 不同但 query 文本相似时不会串库

**退出标准**
- PDK 查询支持 metadata 硬过滤
- 检索链路中具备可替换的 reranker 层
- 数据库异常时 API 不会 500

---

### M4. OpenAI 兼容 Streaming

**目标**
- `/v1/chat/completions` 支持 `stream=true`
- graph 事件可映射为 OpenAI 兼容 chunk
- 为 Open WebUI 展示中间过程打通基础通道

**涉及文件**

修改：
- `jbprag/src/main.py`
- `jbprag/src/graph.py`
- `jbprag/src/response_formatter.py`

新增：
- `jbprag/src/streaming.py`
- `jbprag/tests/test_streaming.py`

**文件级任务**

`jbprag/src/streaming.py`
- 封装 SSE 事件构造
- 定义 token chunk、trace chunk、done chunk 的输出格式

`jbprag/src/response_formatter.py`
- 新增 chat completion chunk formatter
- 统一处理 `delta`、`finish_reason`

`jbprag/src/graph.py`
- 暴露 `invoke` 与 `stream/astream_events` 两套入口
- 事件流中输出 route、retrieval、tool log、final answer 片段

`jbprag/src/main.py`
- 根据 `req.stream` 选择普通响应或 `StreamingResponse`
- 保证流式和非流式共享同一套业务逻辑，而不是两套实现

`jbprag/tests/test_streaming.py`
- 覆盖 SSE 基本结构
- 覆盖最后 `[DONE]`
- 覆盖错误时的流式终止行为

`jbprag/tests/test_api.py`
- 增加 `stream=true` 契约测试

**退出标准**
- `curl` 可见连续 SSE chunk
- Open WebUI 可消费返回
- 非流式路径不回归

---

### M5. EDA Script Expert Agentic Loop

**目标**
- 从 prompt 包装节点升级为“检索 -> 生成 -> 检查 -> 修正”的子图。
- 初期先实现轻量自检或规则检查，后续再接真实 linter。

**涉及文件**

修改：
- `jbprag/src/experts/eda_script_expert.py`
- `jbprag/src/graph.py`

新增：
- `jbprag/src/retrieval/eda_retriever.py`
- `jbprag/src/experts/eda_script_subgraph.py`
- `jbprag/src/prompts/eda_prompt.py`
- `jbprag/src/tools/eda_lint.py`

测试：
- `jbprag/tests/test_eda_expert.py`
- `jbprag/tests/test_eda_subgraph.py`

**文件级任务**

`jbprag/src/retrieval/eda_retriever.py`
- 按 `category=EDA` 和 `tool` 做检索
- 复用统一 retrieval 类型与 reranker

`jbprag/src/prompts/eda_prompt.py`
- 分离“脚本生成 prompt”和“脚本检查 prompt”

`jbprag/src/tools/eda_lint.py`
- 第一版可实现为规则检查器接口
- 支持最小返回格式：`passed`、`issues`、`suggestions`

`jbprag/src/experts/eda_script_subgraph.py`
- 建立 `retrieve -> generate -> lint/check -> refine -> finalize`
- 设置最大循环次数，例如 2 次

`jbprag/src/experts/eda_script_expert.py`
- 从单函数节点升级为调用子图
- 将脚本、检查结果和修订说明写入 state / tool_logs

`jbprag/src/graph.py`
- 接入新的 EDA 子图节点

`jbprag/tests/test_eda_subgraph.py`
- 覆盖一次生成即通过
- 覆盖第一次失败后第二次修正通过
- 覆盖超出最大迭代次数时的退出

**退出标准**
- EDA 请求可以给出脚本、检查结论、假设说明
- 具备最小 agentic loop，而不是单次 prompt

---

### M6. Metrics Analyst: RAG + Text-to-SQL

**目标**
- 支持项目维度的历史文档检索和只读 SQL 查询。
- 让 metrics 查询返回精确数值，而不是纯生成式总结。

**涉及文件**

修改：
- `jbprag/src/experts/metrics_analyst.py`
- `jbprag/dev_data/metrics_seed.sql`

新增：
- `jbprag/src/retrieval/project_retriever.py`
- `jbprag/src/experts/metrics_subgraph.py`
- `jbprag/src/prompts/metrics_prompt.py`
- `jbprag/src/sql/sql_client.py`
- `jbprag/src/sql/sql_guardrails.py`

测试：
- `jbprag/tests/test_metrics_analyst.py`
- `jbprag/tests/test_sql_guardrails.py`
- `jbprag/tests/test_metrics_subgraph.py`

**文件级任务**

`jbprag/src/sql/sql_client.py`
- 封装只读数据库访问
- 统一 SQL 执行、超时、结果格式化
- 第一阶段先对接本地测试 metrics 数据库，后续再迁移到工作环境连接信息

`jbprag/src/sql/sql_guardrails.py`
- 强制只允许 `SELECT`
- 限制 schema / table / view allowlist
- 禁止多语句执行

`jbprag/src/retrieval/project_retriever.py`
- 用于项目文档检索
- 强制依赖 `project_id`

`jbprag/src/prompts/metrics_prompt.py`
- 定义 text-to-sql prompt
- 定义结果总结 prompt

`jbprag/src/experts/metrics_subgraph.py`
- 子图建议：`route(query type) -> generate sql -> validate -> execute -> doc rag -> summarize`

`jbprag/src/experts/metrics_analyst.py`
- 改为调用子图
- 统一返回指标数字、趋势总结、使用到的项目范围

`jbprag/tests/test_sql_guardrails.py`
- 覆盖非 `SELECT` 拒绝
- 覆盖多语句拒绝
- 覆盖 allowlist 限制

`jbprag/tests/test_metrics_subgraph.py`
- 覆盖 SQL 查询分支
- 覆盖纯文档分支
- 覆盖 project_id 缺失时的澄清路径
- 覆盖基于本地 seed 数据返回稳定结果

**退出标准**
- Metrics 查询可输出项目维度精确数据
- 所有 SQL 均经过 guardrail
- project_id 缺失时不允许跨项目宽搜

---

### M7. Ingestion / Indexing 基建

**目标**
- 补齐 spec 中的离线文档入库能力。
- 统一 chunk metadata schema，为所有 expert 共享索引底座。

**涉及文件**

新增：
- `jbprag/src/ingestion/loader.py`
- `jbprag/src/ingestion/chunker.py`
- `jbprag/src/ingestion/metadata_mapper.py`
- `jbprag/src/ingestion/indexer.py`
- `jbprag/src/ingestion/cli.py`
- `jbprag/dev_data/raw_docs/`
- `jbprag/tests/test_ingestion_metadata.py`
- `jbprag/tests/test_indexer.py`

**文件级任务**

`jbprag/src/ingestion/loader.py`
- 加载 PDK、EDA 手册、项目文档
- 输出统一文档对象

`jbprag/src/ingestion/chunker.py`
- 支持按章节/表格感知分块
- 避免粗暴固定长度切分导致表格和层级信息丢失

`jbprag/src/ingestion/metadata_mapper.py`
- 统一产出：`doc_id`、`chunk_id`、`category`、`node`、`tool`、`project_id`、`source`、`section`、`page`、`updated_at`

`jbprag/src/ingestion/indexer.py`
- 负责 embeddings、upsert、增量更新
- 保证重复导入不会产生脏重复

`jbprag/src/ingestion/cli.py`
- 提供离线命令行入口
- 至少支持单目录导入和 dry-run

`jbprag/dev_data/raw_docs/`
- 保存用于 ingestion 演练的原始样例文档
- 与 `pdk_rules.jsonl` / `project_docs.jsonl` 的索引结果保持可追溯关系

`jbprag/tests/test_ingestion_metadata.py`
- 覆盖 metadata 映射正确性

`jbprag/tests/test_indexer.py`
- 覆盖 upsert / duplicate handling

**退出标准**
- 文档可离线入库
- chunk metadata 满足 retrieval hard filter 需求
- 重复导入具备幂等性

---

### M8. 集成加固与验收

**目标**
- 补齐契约测试、异常兜底、真实场景 smoke test。
- 形成可用于阶段验收的最小回归基线。

**涉及文件**

修改：
- `jbprag/tests/test_api.py`
- `jbprag/tests/test_graph.py`

新增：
- `jbprag/tests/test_end_to_end_smoke.py`
- `jbprag/tests/fixtures/`

**文件级任务**

`jbprag/tests/fixtures/`
- 构造冲突样本：
  - `N5` 与 `N7` 相似规则
  - `Innovus` 与 `ICC2` 相似命令
  - `Proj_A` 与 `Proj_B` 相似指标名
- 固化来自本地 seed 数据的稳定断言样本

`jbprag/tests/test_end_to_end_smoke.py`
- PDK 查询 smoke test
- EDA 查询 smoke test
- Metrics 查询 smoke test
- Postgres 不可用降级 smoke test

`jbprag/tests/test_api.py`
- 覆盖非流式和流式
- 覆盖异常响应格式

`jbprag/tests/test_graph.py`
- 覆盖 supervisor + expert + finalizer 全链路

**退出标准**
- 关键主链路具备稳定回归测试
- 错误场景行为确定且可验证

## 5. 测试清单

### 5.1 单元测试

- `test_message_utils.py`
  - 多轮消息转换
  - role 保真
- `test_supervisor.py`
  - 路由分类
  - metadata 抽取
  - 非法 JSON 降级
- `test_vector_store.py`
  - metadata filter 查询封装
- `test_settings.py`
  - 配置加载
  - reranker 默认模型
- `test_dev_seed_data.py`
  - 本地样例数据完整性
- `test_pdk_retriever.py`
  - hard filter
  - reranker 调用
  - 空结果/异常降级
- `test_eda_subgraph.py`
  - 生成
  - 检查
  - 修正循环
- `test_sql_guardrails.py`
  - 只读 SQL 限制
  - allowlist
- `test_indexer.py`
  - upsert
  - 幂等导入

### 5.2 契约测试

- `test_api.py`
  - `GET /v1/models`
  - `POST /v1/chat/completions` 非流式
  - `POST /v1/chat/completions` 流式
  - OpenAI 风格响应结构
- `test_streaming.py`
  - SSE chunk 结构
  - `[DONE]`
  - 错误中断

### 5.3 集成测试

- `test_end_to_end_smoke.py`
  - PDK：`What is N5 M3 pitch?`
  - EDA：`Write an Innovus Tcl snippet to create floorplan`
  - Metrics：`Summarize timing/power history for Proj_A`
  - 异常：停掉 Postgres 后发起 PDK 查询
- `seed_dev_data.py`
  - 本地向量库和 metrics 数据初始化成功

### 5.4 人工验收清单

- Open WebUI 能消费 `stream=true` 响应
- PDK 问题在不同 `node` 上不会串结果
- EDA 问题能返回脚本和检查反馈
- Metrics 问题能返回项目内精确数值
- 数据库/向量库异常时，服务不 500 且返回可理解降级信息

## 6. 推荐提交策略

- 每个里程碑至少一个独立提交
- 大里程碑内部建议按“底层抽象 -> expert 接入 -> 测试”拆成 2 到 4 个提交
- 禁止把 streaming、EDA loop、Metrics SQL 混在同一个提交中

推荐提交粒度：
- `chore: upgrade langchain stack and add dev seed data`
- `refactor: normalize chat request and graph state`
- `feat: add supervisor metadata extraction`
- `feat: add pdk metadata filtered retrieval pipeline`
- `feat: support streaming chat completions`
- `feat: implement eda expert refinement loop`
- `feat: add metrics sql analyst subgraph`
- `feat: add ingestion and indexing pipeline`
- `test: add end-to-end smoke coverage`

## 7. 已确认决策与剩余风险

**已确认决策**
- 依赖版本先升级：`langchain` / `langgraph` 相关升级工作前置到 M0。
- reranker 采用 `qwen3-reranker-8b` 试跑，配置来源于本地模型配置文件和环境变量，不在代码中硬编码敏感信息。
- 向量数据库和 metrics 当前阶段均使用自建本地测试数据与种子脚本，真实工作环境接入后置。

**剩余风险**
- 升级依赖后，LangGraph 状态定义、streaming API、消息对象接口可能发生兼容性变化，需要在 M0 做一次集中消解。
- `qwen3-reranker-8b` 的调用协议需要在实现时验证；如果服务端不是标准 OpenAI 兼容接口，需要单独封装 client。
- 本地测试 metrics schema 与未来工作环境 schema 可能不完全一致，因此 `sql_guardrails.py` 和 `sql_client.py` 要避免把当前测试表名写死到高层逻辑。
- Open WebUI 对 trace / tool log 的展示兼容方式仍需在 M4 前确认，但这不会阻塞 M0-M3。
