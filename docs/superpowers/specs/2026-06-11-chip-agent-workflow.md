# Jbprag 工作流与系统集成设计图

下面是 `jbprag` 的核心流程图。它展示了整个系统是如何与 Open WebUI 进行对接的，以及内部基于 LangGraph 的多智能体工作流（Supervisor → Experts → Subgraphs）是如何协同工作的。

## 系统架构与工作流示意图

```mermaid
graph TD
    %% -- 用户与前端 --
    User((User))
    OWUI["Open WebUI (Frontend)"]
    
    User -->|交互输入 / 展示| OWUI
    OWUI --> User
    
    %% -- 边界与接口层 --
    subgraph Backend [Jbpragic RAG Backend Service]
        API["FastAPI Endpoint (POST /v1/chat/completions)"]
        StreamAdapter["Streaming Adapter (SSE Generator)"]
        
        %% -- LangGraph 核心图 --
        subgraph Graph [LangGraph StateGraph]
            Supervisor["Supervisor Node (意图分类 & 元数据提取)"]
            
            %% PDK 专家
            subgraph PDK_Pipeline [PDK Expert Pipeline]
                PDK_Retriever["PDK Retriever (Filter + Vector Search + Rerank)"]
                PDK_Gen["PDK Answer Generator"]
            end
            
            %% EDA 脚本专家子图
            subgraph EDA_Subgraph [EDA Script Expert Subgraph]
                EDA_Retriever["EDA Manual Retriever"]
                EDA_Gen["Script Generator"]
                EDA_Lint["Linter Guardrail (括号配对、危险命令检查)"]
                EDA_Refine["Refinement Agent (根据 Lint 报错自我修正)"]
            end
            
            %% 指标分析专家子图
            subgraph Metrics_Subgraph [Metrics Analyst Subgraph]
                Met_Route{"Query Router (SQL / Docs / Both)"}
                Met_SQL_Gen["Text-to-SQL Generator"]
                Met_SQL_Val["SQL Validator (防止注入、越权读写)"]
                Met_SQL_Exec["SQL Executor"]
                Met_Doc_Ret["Project Doc Retriever"]
                Met_Sum["Result Summarizer"]
            end
            
            Finalizer["Finalizer Node (状态收集与格式化)"]
        end
    end
    
    %% -- 外部存储系统 --
    DB_Vec[("PGVector (PDK/EDA/Project 知识库)")]
    DB_Metrics[("PostgreSQL (Metrics/Project 数据)")]

    %% -- 系统对接逻辑 --
    %% Open WebUI 作为标准的 OpenAI 客户端，通过 OpenAI API 格式与 FastAPI 对接
    OWUI -->|兼容 OpenAI API 规范| API
    API --> OWUI
    
    %% 接口层到图的入口
    API -->|初始化 AgentState| Supervisor
    %% 流式输出通过 LangGraph astream_events 直接推送到前端
    StreamAdapter -.->|Yield 实时生成的 Chunk| API
    
    %% -- 路由逻辑 --
    Supervisor -->|route: pdk_expert| PDK_Retriever
    Supervisor -->|route: eda_script_expert| EDA_Retriever
    Supervisor -->|route: metrics_analyst| Met_Route
    Supervisor -->|route: finalizer| Finalizer

    %% -- PDK 内部流向 --
    PDK_Retriever --> DB_Vec
    DB_Vec --> PDK_Retriever
    PDK_Retriever --> PDK_Gen
    PDK_Gen --> Finalizer
    PDK_Gen -.->|Stream on_chat_model_stream| StreamAdapter

    %% -- EDA 内部流向 (Agentic Loop) --
    EDA_Retriever --> DB_Vec
    DB_Vec --> EDA_Retriever
    EDA_Retriever --> EDA_Gen
    EDA_Gen --> EDA_Lint
    EDA_Lint -->|Lint Fail| EDA_Refine
    EDA_Refine --> EDA_Lint
    EDA_Lint -->|Lint Pass 或 达到最大迭代| Finalizer
    EDA_Gen -.->|Stream on_chat_model_stream| StreamAdapter
    EDA_Refine -.->|Stream on_chat_model_stream| StreamAdapter

    %% -- Metrics 内部流向 (混合双路) --
    Met_Route -->|sql/both| Met_SQL_Gen
    Met_Route -->|docs/both| Met_Doc_Ret
    
    Met_SQL_Gen --> Met_SQL_Val
    Met_SQL_Val -->|Valid| Met_SQL_Exec
    Met_SQL_Val -->|Invalid| Met_SQL_Gen
    Met_SQL_Exec --> DB_Metrics
    DB_Metrics --> Met_SQL_Exec
    
    Met_Doc_Ret --> DB_Vec
    DB_Vec --> Met_Doc_Ret
    
    Met_SQL_Exec --> Met_Sum
    Met_Doc_Ret --> Met_Sum
    Met_Sum --> Finalizer
    Met_Sum -.->|Stream on_chat_model_stream| StreamAdapter

    %% -- 出口逻辑 --
    Finalizer -->|Non-Streaming 回复| API
```

## 与 Open WebUI 对接原理解析

### 1. 协议伪装 (API Compatibility)
Open WebUI 原本设计为直接与 OpenAI (或其他标准模型) 的服务器通信。`jbprag` 利用 FastAPI 提供了一个完全兼容 OpenAI `ChatCompletion` 格式的接口：
- 暴露 `GET /v1/models`，伪装成拥有名为 `jbprag` 模型的服务器。
- 暴露 `POST /v1/chat/completions` 作为聊天入口。
- WebUI 只需要在设置中添加一个新的 OpenAI Connection，将 URL 指向 `http://<jbprag_ip>:<port>/v1` 并随便填入一个 key，即可将请求打给后端系统。

### 2. 状态映射 (State Mapping)
- **请求进来时**：FastAPI 层拦截到标准的 `messages` (如 `[{"role": "user", "content": "..."}]`)，通过工具函数转成 LangChain 内部的 `HumanMessage` / `SystemMessage` 对象，并用其初始化 LangGraph 的第一帧 `AgentState`。
- **响应出去时**：如果是普通的非流式请求，系统等图跑完了，把 `finalizer` 最后生成的那段话包装成 OpenAI response json 结构发回给 WebUI。

### 3. 流式交互 (Streaming Adapter)
Open WebUI 的灵魂在于打字机体验。后端是如何实现它的？
- `jbprag` 并没有简单地等全部跑完再返回，而是使用了 LangGraph 的异步事件流（`astream_events`）。
- 只有真正的 Expert 节点（例如 PDK 生成器、EDA 脚本生成器）产生新的 Token 时触发的 `on_chat_model_stream` 事件会被捕捉到。
- `Streaming Adapter` 将拦截到的各个 Token 包成 Server-Sent Events (SSE)，这就实现了与普通大模型完全一样的逐字显现效果。
- 中间的 Supervisor 路由思考、Lint 修正等动作（通常不触发 chat stream），对用户而言都是透明发生的，这为多步骤 Agent 隐藏了底层的复杂跳跃，最终只让用户看到提纯后的回答。
