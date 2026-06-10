# Chip Backend Agentic RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone FastAPI + LangGraph MVP backend for the Chip Agentic RAG system, implementing PostgreSQL vector storage, a Supervisor Router, and a PDK Expert pipeline, exposing an OpenAI-compatible API endpoint.

**Architecture:** A FastAPI service mimicking OpenAI's chat endpoint. It receives queries, passes them to a LangGraph Supervisor, which classifies the intent. If it's a PDK query, it routes to a PDK Expert that performs a vector search on a PostgreSQL database.

**Tech Stack:** FastAPI, LangGraph, LangChain, pytest, psycopg2-binary, pgvector.

---

### Task 1: Initialize Project Structure and Dependencies

**Files:**
- Create: `chip_agent/requirements.txt`
- Create: `chip_agent/tests/conftest.py`

- [x] **Step 1: Write requirements**

```text
fastapi==0.111.0
uvicorn==0.29.0
langchain==0.2.1
langgraph==0.0.55
langchain-openai==0.1.7
langchain-postgres==0.0.9
psycopg2-binary==2.9.9
pgvector==0.2.5
pytest==8.2.1
pytest-asyncio==0.23.6
```

- [x] **Step 2: Write pytest configuration**

```python
import pytest

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
```

- [x] **Step 3: Commit**

```bash
git add chip_agent/requirements.txt chip_agent/tests/conftest.py
git commit -m "chore: init chip agent project structure and deps"
```

### Task 2: Implement PostgreSQL Vector Store Interface

**Files:**
- Create: `chip_agent/tests/test_vector_store.py`
- Create: `chip_agent/src/vector_store.py`

- [ ] **Step 1: Write the failing test**

```python
from src.vector_store import get_vector_store
from langchain_core.embeddings import FakeEmbeddings

def test_get_vector_store():
    embeddings = FakeEmbeddings(size=1536)
    store = get_vector_store(
        connection_string="postgresql+psycopg://user:pass@localhost:5432/db",
        collection_name="test_col",
        embeddings=embeddings
    )
    assert store.collection_name == "test_col"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest chip_agent/tests/test_vector_store.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.vector_store'"

- [ ] **Step 3: Write minimal implementation**

```python
from langchain_postgres import PGVector
from langchain_core.embeddings import Embeddings

def get_vector_store(connection_string: str, collection_name: str, embeddings: Embeddings) -> PGVector:
    return PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=chip_agent pytest chip_agent/tests/test_vector_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add chip_agent/tests/test_vector_store.py chip_agent/src/vector_store.py
git commit -m "feat: implement pgvector store interface"
```

### Task 3: Implement PDK Expert Node

**Files:**
- Create: `chip_agent/tests/test_pdk_expert.py`
- Create: `chip_agent/src/experts/pdk_expert.py`

- [ ] **Step 1: Write the failing test**

```python
from src.experts.pdk_expert import pdk_expert_node
from langchain_core.messages import HumanMessage, AIMessage

def test_pdk_expert_node():
    state = {"messages": [HumanMessage(content="What is N5 M3 pitch?")]}
    result = pdk_expert_node(state)
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert "PDK" in result["messages"][0].content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=chip_agent pytest chip_agent/tests/test_pdk_expert.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
from typing import TypedDict, List
from langchain_core.messages import AnyMessage, AIMessage

class AgentState(TypedDict):
    messages: List[AnyMessage]

def pdk_expert_node(state: AgentState) -> dict:
    query = state["messages"][-1].content
    # MVP: Mock retrieval and response. In production, this calls the VectorStore from Task 2.
    mock_response = f"[PDK Expert] Processed query: {query}. The M3 pitch for N5 is 36nm."
    return {"messages": [AIMessage(content=mock_response)]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=chip_agent pytest chip_agent/tests/test_pdk_expert.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add chip_agent/tests/test_pdk_expert.py chip_agent/src/experts/pdk_expert.py
git commit -m "feat: implement mock PDK expert node"
```

### Task 4: Implement Supervisor Router & LangGraph

**Files:**
- Create: `chip_agent/tests/test_graph.py`
- Create: `chip_agent/src/graph.py`

- [ ] **Step 1: Write the failing test**

```python
from src.graph import build_graph
from langchain_core.messages import HumanMessage

def test_graph_routing():
    graph = build_graph()
    result = graph.invoke({"messages": [HumanMessage(content="What is N5 M3 pitch?")]})
    assert len(result["messages"]) > 1
    assert "PDK" in result["messages"][-1].content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=chip_agent pytest chip_agent/tests/test_graph.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, AIMessage
from typing import TypedDict, List
import operator
from src.experts.pdk_expert import pdk_expert_node

class AgentState(TypedDict):
    messages: List[AnyMessage]

def supervisor_node(state: AgentState) -> dict:
    # MVP Supervisor: blindly routes everything to PDK expert for now
    return {"messages": []}

def router(state: AgentState) -> str:
    # MVP Router: always returns "pdk_expert"
    return "pdk_expert"

def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("pdk_expert", pdk_expert_node)
    
    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges("supervisor", router, {"pdk_expert": "pdk_expert"})
    workflow.add_edge("pdk_expert", END)
    
    return workflow.compile()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=chip_agent pytest chip_agent/tests/test_graph.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add chip_agent/tests/test_graph.py chip_agent/src/graph.py
git commit -m "feat: implement langgraph supervisor and routing"
```

### Task 5: Implement FastAPI Endpoint

**Files:**
- Create: `chip_agent/tests/test_api.py`
- Create: `chip_agent/src/main.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_chat_completions():
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "What is N5 M3 pitch?"}]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert "PDK" in data["choices"][0]["message"]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=chip_agent pytest chip_agent/tests/test_api.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from src.graph import build_graph
from langchain_core.messages import HumanMessage
import time
import uuid

app = FastAPI()
graph = build_graph()

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: str = "default"

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    last_msg = req.messages[-1]["content"]
    result = graph.invoke({"messages": [HumanMessage(content=last_msg)]})
    final_text = result["messages"][-1].content
    
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": final_text
            },
            "finish_reason": "stop"
        }]
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=chip_agent pytest chip_agent/tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add chip_agent/tests/test_api.py chip_agent/src/main.py
git commit -m "feat: add openai compatible chat completions endpoint"
```
