- [x] **Task 1: Requirements & Config Upgrade**
    - [x] Step 1: Modify `jbprag/requirements.txt` with new versions
    - [x] Step 2: Install updated packages in WSL virtual environment
    - [x] Step 3: Create `jbprag/src/settings.py`
    - [x] Step 4: Modify `jbprag/src/utils.py` to use settings
    - [x] Step 5: Create `jbprag/tests/test_settings.py`
    - [x] Step 6: Verify config and settings tests pass
- [x] **Task 2: Dev Seed Data Creation**
    - [x] Step 1: Create `jbprag/dev_data/README.md`
    - [x] Step 2: Create `jbprag/dev_data/pdk_rules.jsonl`
    - [x] Step 3: Create `jbprag/dev_data/eda_manuals.jsonl`
    - [x] Step 4: Create `jbprag/dev_data/project_docs.jsonl`
    - [x] Step 5: Create `jbprag/dev_data/metrics_seed.sql`
    - [x] Step 6: Create `jbprag/tests/test_dev_seed_data.py`
    - [x] Step 7: Verify seed data tests pass
- [x] **Task 3: Seed Script & Dependency Smoke Test**
    - [x] Step 1: Create `jbprag/scripts/seed_dev_data.py`
    - [x] Step 2: Create `jbprag/tests/test_dependency_smoke.py`
    - [x] Step 3: Run all pytest suites to verify M0 correctness
    - [x] Step 4: Commit M0 changes to Git

- [x] **Task 4: State & API Model Definitions**
    - [x] Step 1: Create `jbprag/src/state.py`
    - [x] Step 2: Create `jbprag/src/api_models.py`

- [x] **Task 5: Adapter & Utility Layer Implementation**
    - [x] Step 1: Create `jbprag/src/message_utils.py`
    - [x] Step 2: Create `jbprag/src/response_formatter.py`

- [x] **Task 6: Graph & FastAPI Endpoint Refactoring**
    - [x] Step 1: Modify `jbprag/src/graph.py`
    - [x] Step 2: Modify `jbprag/src/main.py`

- [x] **Task 7: Test implementation & validation**
    - [x] Step 1: Create `jbprag/tests/test_message_utils.py`
    - [x] Step 2: Update `jbprag/tests/test_graph.py`
    - [x] Step 3: Update `jbprag/tests/test_api.py`
    - [x] Step 4: Run all pytest suites to verify M1 correctness

- [x] **Task 8: Metadata & Prompts Implementation**
    - [x] Step 1: Create `jbprag/src/metadata.py`
    - [x] Step 2: Create `jbprag/src/prompts/supervisor_prompt.py`

- [x] **Task 9: Supervisor Node Implementation**
    - [x] Step 1: Create `jbprag/src/supervisor.py`

- [x] **Task 10: Graph Refactoring**
    - [x] Step 1: Modify `jbprag/src/graph.py`

- [x] **Task 11: M2 Test Implementation & Verification**
    - [x] Step 1: Create `jbprag/tests/test_supervisor.py`
    - [x] Step 2: Update `jbprag/tests/test_graph.py`
    - [x] Step 3: Run all pytest suites to verify M2 correctness

- [x] **Task 12: Milestone M3 - PDK Retrieval Upgrade**
    - [x] Step 1: Create `jbprag/src/retrieval/types.py`
    - [x] Step 2: Create `jbprag/src/retrieval/reranker.py`
    - [x] Step 3: Create `jbprag/src/prompts/pdk_prompt.py`
    - [x] Step 4: Create `jbprag/src/retrieval/pdk_retriever.py`
    - [x] Step 5: Modify `jbprag/src/vector_store.py`
    - [x] Step 6: Modify `jbprag/src/experts/pdk_expert.py`
    - [x] Step 7: Create `jbprag/tests/test_pdk_retriever.py`
    - [x] Step 8: Update `jbprag/tests/test_pdk_expert.py` and verify M3 passes

- [x] **Task 13: Milestone M4 - OpenAI Compatible Streaming**
    - [x] Step 1: Create `jbprag/src/streaming.py`
    - [x] Step 2: Modify `jbprag/src/response_formatter.py`
    - [x] Step 3: Modify `jbprag/src/main.py`
    - [x] Step 4: Create `jbprag/tests/test_streaming.py`
    - [x] Step 5: Update `jbprag/tests/test_api.py` and verify M4 passes

- [x] **Task 14: Milestone M5 - EDA Script Expert Subgraph**
    - [x] Step 1: Create `jbprag/src/tools/eda_lint.py`
    - [x] Step 2: Create `jbprag/src/retrieval/eda_retriever.py`
    - [x] Step 3: Create `jbprag/src/prompts/eda_prompt.py`
    - [x] Step 4: Create `jbprag/src/experts/eda_script_subgraph.py`
    - [x] Step 5: Modify `jbprag/src/experts/eda_script_expert.py` and `jbprag/src/graph.py`
    - [x] Step 6: Create `jbprag/tests/test_eda_subgraph.py`
    - [x] Step 7: Run all tests to verify M0-M5 correctness
