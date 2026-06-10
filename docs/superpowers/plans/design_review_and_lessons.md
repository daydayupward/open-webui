# Design Review & Lessons Learned: Chip Agentic RAG

This document reviews the current MVP implementation of the Chip Backend Design Agentic RAG system against its original specification ([2026-06-10-chip-agentic-rag-design.md](file:///Ubuntu/home/eason/proj/open-webui/docs/superpowers/specs/2026-06-10-chip-agentic-rag-design.md)) and extracts valuable technical experiences.

---

## 1. Feature Review (Spec vs. Implementation)

| Spec Section | Requirement | Current Status | Notes / Gaps |
| :--- | :--- | :--- | :--- |
| **Frontend / API** | OpenAI-compatible `/v1/chat/completions` API endpoint | **Fully Implemented** | Handled in [main.py](file:///Ubuntu/home/eason/proj/open-webui/chip_agent/src/main.py) and verified by end-to-end tests. |
| **Orchestration** | LangGraph StateGraph with Supervisor Router | **Implemented (MVP)** | [graph.py](file:///Ubuntu/home/eason/proj/open-webui/chip_agent/src/graph.py) contains the graph setup. The router currently routes blindly to the PDK Expert. |
| **Vector Store** | PostgreSQL + `pgvector` interface | **Implemented** | [vector_store.py](file:///Ubuntu/home/eason/proj/open-webui/chip_agent/src/vector_store.py) encapsulates the LangChain `PGVector` store initialization. |
| **Sub-Agent: PDK Expert** | Node rules, DRC limitations, SPICE parameters | **Mocked (MVP)** | Returns a mock response in [pdk_expert.py](file:///Ubuntu/home/eason/proj/open-webui/chip_agent/src/experts/pdk_expert.py). Needs database integration. |
| **Sub-Agent: EDA Script Expert** | Tool manuals, Tcl/Skill script generator (Agentic loops) | *Not Started* | To be implemented in next phase. |
| **Sub-Agent: Metrics Analyst** | Mixed (Text-to-SQL + Project Docs RAG) | *Not Started* | To be implemented in next phase. |

---

## 2. Key Gaps to Address for Production

1. **Routing Logic Expansion**:
   The current `router` in `graph.py` blindly returns `"pdk_expert"`. In production, this must use an LLM-based classifier or metadata parser to select the correct expert (`pdk_expert`, `eda_script_expert`, `metrics_analyst`).
2. **Actual Vector Retrieval**:
   The PDK Expert currently returns hardcoded mock content. It should be wired to use the vector store interface implemented in `vector_store.py` to perform similarity searches with metadata filters (e.g., filtering by `node="N5"` or `tool="Innovus"`).
3. **Streaming Event Parsing**:
   For large language model outputs, standard HTTP responses should be converted to Server-Sent Events (SSE) to allow Open WebUI to stream responses dynamically instead of waiting for the full graph completion.

---

## 3. Valuable Lessons Learned & Best Practices

### A. TDD & Isolation of External Dependencies in Testing
* **The Problem**: During unit testing, calling `get_vector_store` attempted to establish a real connection to `localhost:5432` to create the `pgvector` extension, resulting in `ConnectionRefusedError`.
* **The Experience**: Mocking the instantiation of `PGVector` using `unittest.mock.patch` allows verifying that parameters (endpoints, database credentials, embedding functions) are correctly forwarded without relying on database uptime during CI/CD test phases.

### B. Python Environment Stability in WSL / Lightweight Linux
* **The Problem**: LangChain's new PostgreSQL extension `langchain-postgres` relies on `psycopg` (v3). Running pytest on standard environments raised `ImportError: no pq wrapper available` due to missing libpq C libraries.
* **The Experience**: Using `uv pip install "psycopg[binary]"` resolved this by using pre-compiled binaries, removing the need for manual C-compilation on host operating systems. Using `uv` guarantees predictable and fast dependency installation.

### C. LangGraph State Propagation
* **The Problem**: Without custom state merging logic, when a sub-agent outputs new messages, they overwrite the current state's messages rather than accumulating them.
* **The Experience**: Utilizing `Annotated[List[AnyMessage], operator.add]` as a reducer is mandatory in LangGraph message-passing workflows. It enables seamless conversation history accumulation, making tests like `assert len(result["messages"]) > 1` pass reliably.
