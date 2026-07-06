# Walkthrough: Chip Backend Agentic RAG System - Milestones M3, M4, and M5

We have successfully completed the implementation and verification of **Milestone M3** (PDK Retrieval Upgrade), **Milestone M4** (OpenAI-compatible Streaming), and **Milestone M5** (EDA Script Expert Agentic Subgraph).

---

## Completed Work

### 1. Milestone M3: PDK Retrieval Upgrade
- **Standard RAG Interfaces** ([types.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/retrieval/types.py)): Defined unified classes `RetrievalChunk`, `RetrievalRequest`, and `RetrievalResult`.
- **Qwen Reranker** ([reranker.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/retrieval/reranker.py)): Implemented `QwenRerankerClient` supporting the `qwen3-reranker-8b` model and standard request schemas, with a fallback `IdentityReranker` to ensure local tests pass even when offline.
- **Retrieval Pipeline** ([pdk_retriever.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/retrieval/pdk_retriever.py)): Integrated metadata hard filtering, similarity search query, and reranker execution.
- **PDK Expert Node** ([experts/pdk_expert.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/experts/pdk_expert.py)): Integrated the retrieve pipeline, appending retrieved document chunks to `retrieved_docs` and logging events in `tool_logs`.

### 2. Milestone M4: OpenAI Compatible Streaming
- **SSE Stream Generator** ([streaming.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/streaming.py)): Built `astream_chat_completion_events` which filters and streams tokens from active expert nodes by hook-listening on LangGraph's `astream_events("v2")`.
- **API Response Wrapper** ([main.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/main.py)): Added FastAPI `StreamingResponse` for requests specifying `stream=True`.
- **Chunk Formatting** ([response_formatter.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/response_formatter.py)): Extracted `format_openai_chunk` to produce standard OpenAI delta chunks.

### 3. Milestone M5: EDA Script Expert Subgraph
- **Tcl/Skill Linter** ([tools/eda_lint.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/tools/eda_lint.py)): Developed a bracket-checking stack validation along with verification for restricted command names (`exec`, `system`, `sh`, `bash`, `exit`, `rm`, `mv`, `socket`).
- **EDA Retriever** ([retrieval/eda_retriever.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/retrieval/eda_retriever.py)): Implemented a pgvector search filtering for `category="EDA"` and the requested physical design tool.
- **EDA Prompts** ([prompts/eda_prompt.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/prompts/eda_prompt.py)): Separated generation and linter refinement templates.
- **Agentic Subgraph** ([experts/eda_script_subgraph.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/experts/eda_script_subgraph.py)): Constructed a LangGraph workflow with nodes: `retrieve` -> `generate` -> `lint` -> `refine` (repeating `lint` up to 2 iterations if check fails).
- **Expert Node Refactoring** ([experts/eda_script_expert.py](file:///Ubuntu/home/eason/proj/open-webui/jbprag/src/experts/eda_script_expert.py)): Replaced the prompt-only node with synchronous execution of the new compiled subgraph, successfully merging updates (messages, retrieved documents, and linter check logs) into the parent `AgentState`.

---

## Verification Outcomes

All 31 tests in the project test suite pass successfully:

```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.2.1, pluggy-1.6.0 -- /home/eason/proj/open-webui/jbprag/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /home/eason/proj/open-webui
configfile: pyproject.toml
plugins: asyncio-0.23.6, anyio-4.13.0
asyncio: mode=Mode.STRICT
collecting ... collected 31 items

jbprag/tests/test_api.py::test_chat_completions PASSED               [  3%]
jbprag/tests/test_api.py::test_chat_completions_multi_turn PASSED    [  6%]
jbprag/tests/test_api.py::test_chat_completions_streaming PASSED     [  9%]
jbprag/tests/test_api.py::test_list_models PASSED                    [ 12%]
jbprag/tests/test_dependency_smoke.py::test_imports PASSED           [ 16%]
jbprag/tests/test_dependency_smoke.py::test_model_initialization PASSED [ 19%]
jbprag/tests/test_dev_seed_data.py::test_pdk_rules_format PASSED     [ 22%]
jbprag/tests/test_dev_seed_data.py::test_eda_manuals_format PASSED   [ 25%]
jbprag/tests/test_project_docs_format PASSED                         [ 29%]
jbprag/tests/test_eda_subgraph.py::test_extract_script PASSED        [ 32%]
jbprag/tests/test_eda_subgraph.py::test_eda_linter PASSED            [ 35%]
jbprag/tests/test_eda_subgraph.py::test_retrieve_eda_manuals PASSED  [ 38%]
jbprag/tests/test_eda_subgraph.py::test_subgraph_success_first_attempt PASSED [ 41%]
jbprag/tests/test_eda_subgraph.py::test_subgraph_refinement_loop PASSED [ 45%]
jbprag/tests/test_eda_subgraph.py::test_subgraph_max_iterations_threshold PASSED [ 48%]
jbprag/tests/test_experts.py::test_eda_script_expert PASSED          [ 51%]
jbprag/tests/test_experts.py::test_metrics_analyst PASSED            [ 54%]
jbprag/tests/test_graph.py::test_graph_routing PASSED                [ 58%]
jbprag/tests/test_message_utils.py::test_openai_to_langchain_pydantic PASSED [ 61%]
jbprag/tests/test_message_utils.py::test_openai_to_langchain_dicts PASSED [ 64%]
jbprag/tests/test_pdk_expert.py::test_pdk_expert_node PASSED         [ 67%]
jbprag/tests/test_pdk_retriever.py::test_retrieve_pdk_rules_success PASSED [ 70%]
jbprag/tests/test_pdk_retriever.py::test_retrieve_pdk_rules_fallback_on_db_error PASSED [ 74%]
jbprag/tests/test_settings.py::test_settings_defaults PASSED         [ 77%]
jbprag/tests/test_settings.py::test_settings_override PASSED         [ 80%]
jbprag/tests/test_streaming.py::test_astream_chat_completion_events PASSED [ 83%]
jbprag/tests/test_supervisor.py::test_metadata_normalization PASSED  [ 87%]
jbprag/tests/test_supervisor.py::test_parse_json_safely PASSED       [ 90%]
jbprag/tests/test_supervisor.py::test_run_supervisor_success PASSED  [ 93%]
jbprag/tests/test_supervisor.py::test_run_supervisor_fallback_on_invalid_json PASSED [ 96%]
jbprag/tests/test_vector_store.py::test_get_vector_store PASSED      [100%]

======================== 31 passed, 1 warning in 3.66s =========================
```
