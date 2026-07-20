# Implementation Plan: Milestones M3, M4, and M5

This plan details the implementations of **Milestone M3** (PDK Retrieval Upgrade), **Milestone M4** (OpenAI-compatible Streaming), and **Milestone M5** (EDA Script Expert Agentic Subgraph).

## User Review Required

> [!IMPORTANT]
> **Reranker and Vector Store Fallbacks**:
> For PDK retrieval, we will connect to the `qwen3-reranker-8b` model. To ensure offline local development works when the remote server is offline, we will implement an `IdentityReranker` fallback that preserves the original vector search ranking on connection failures.
>
> **Streaming Implementation**:
> We will implement streaming in `/v1/chat/completions` using FastAPI's `StreamingResponse` wrapping Server-Sent Events (SSE). Tokens will be streamed by capturing LangGraph's `astream_events`, selectively streaming tokens from the expert node's chat completions while suppressing intermediate routing tokens from the supervisor.
>
> **EDA Subgraph Refinement Loop**:
> The EDA Script Expert will be upgraded to an agentic subgraph containing a lint validation check. If validation fails, the subgraph will automatically invoke a refinement prompt to correct the script, with a maximum loop threshold of 2 iterations to avoid infinite LLM generation loops.

---

## Proposed Changes

### Milestone M3: PDK Retrieval Upgrade

#### [NEW] [types.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/retrieval/types.py)
* Define data classes/models for standard RAG interfaces:
  * `RetrievalChunk` (content, metadata, optional score)
  * `RetrievalRequest` (query, filter, top_k)
  * `RetrievalResult` (list of chunks)

#### [NEW] [reranker.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/retrieval/reranker.py)
* Implement `QwenRerankerClient` to call `qwen3-reranker-8b` at `settings.rerank_base_url`.
* Implement `IdentityReranker` as a fallback when the remote reranker is unavailable.

#### [NEW] [pdk_retriever.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/retrieval/pdk_retriever.py)
* Pipeline:
  1. Build a strict metadata filter (e.g. `{"node": metadata["node"], "category": "PDK"}`).
  2. Query `vector_store.similarity_search` with filter.
  3. Rerank results and select top chunks.

#### [NEW] [pdk_prompt.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/prompts/pdk_prompt.py)
* Move PDK-specific prompt definitions and guidelines out of expert code.

#### [MODIFY] [vector_store.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/vector_store.py)
* Expose similarity search helper supporting metadata filtering parameters.

#### [MODIFY] [experts/pdk_expert.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/experts/pdk_expert.py)
* Rewrite `pdk_expert_node` to consume `pdk_retriever` instead of calling PGVector directly.
* Append retrieval logs and scores to `tool_logs` and `retrieved_docs`.

---

### Milestone M4: OpenAI Compatible Streaming

#### [NEW] [streaming.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/streaming.py)
* Implement SSE chunk formattings matching the OpenAI stream spec:
  * `data: {...}`
  * `data: [DONE]`
* Implement a generator that consumes LangGraph's `astream_events` (filtering and yielding only tokens from the active expert node's chat model run).

#### [MODIFY] [main.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/main.py)
* Handle `stream=True` requests by returning a FastAPI `StreamingResponse`.

#### [MODIFY] [response_formatter.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/response_formatter.py)
* Add support for mapping individual token chunks into OpenAI `ChatCompletionChunk` responses.

---

### Milestone M5: EDA Script Expert Subgraph

#### [NEW] [eda_lint.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/tools/eda_lint.py)
* Create a lightweight validation tool checking Tcl syntax commands (bracket validation, restricted commands lists).

#### [NEW] [eda_retriever.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/retrieval/eda_retriever.py)
* Standard retrieval pipeline mapping to `EDA` manuals with tool filters.

#### [NEW] [eda_prompt.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/prompts/eda_prompt.py)
* Define prompt templates for:
  * Script generation (using manuals context)
  * Script refinement (using linter feedback)

#### [NEW] [eda_script_subgraph.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/experts/eda_script_subgraph.py)
* Implement the sub-workflow in LangGraph:
  * Nodes: `retrieve` -> `generate` -> `lint` -> `refine`
  * Conditional routing: Check linter outcome. If failed and under loop threshold (max 2 attempts), route to `refine`, else route to `END`.

#### [MODIFY] [experts/eda_script_expert.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/experts/eda_script_expert.py)
* Update `eda_script_expert_node` to execute the new EDA sub-graph and write outputs to the parent state.

---

## Verification Plan

### Automated Tests
Run tests inside the WSL environment:
- **M3**:
  - `PYTHONPATH=jbprag jbprag/.venv/bin/python3 -m pytest jbprag/tests/test_pdk_retriever.py -v`
  - `PYTHONPATH=jbprag jbprag/.venv/bin/python3 -m pytest jbprag/tests/test_pdk_expert.py -v`
- **M4**:
  - `PYTHONPATH=jbprag jbprag/.venv/bin/python3 -m pytest jbprag/tests/test_streaming.py -v`
- **M5**:
  - `PYTHONPATH=jbprag jbprag/.venv/bin/python3 -m pytest jbprag/tests/test_eda_subgraph.py -v`
- **Full Suite**:
  - `PYTHONPATH=jbprag jbprag/.venv/bin/python3 -m pytest -v`
