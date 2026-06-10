# Chip Backend Design Agentic RAG System

## 1. Overview
This project introduces a standalone Agentic RAG backend service designed to integrate with Open WebUI via an OpenAI-compatible API (`/v1/chat/completions`). It targets the highly specialized domain of chip physical design (backend), addressing the specific challenges of heterogeneous data (EDA manuals, PDK documents, project history, and metrics databases) across multiple strict partitions (nodes, tools, projects).

## 2. Architecture & Data Flow
- **Frontend**: Open WebUI handles user interaction and streams responses.
- **Backend**: A dedicated FastAPI + LangGraph application.
  - Exposes an OpenAI-compatible endpoint.
  - Converts LangGraph state/streaming events into standard chat completions to allow Open WebUI to display intermediate "thoughts" or tool-use logs.
- **Orchestration**: A Multi-Agent Supervisor architecture manages the flow.
  - The **Supervisor Agent** performs Intent Classification and extracts Metadata (e.g., `Tool=Innovus`, `Node=N5`, `Project=ProjA`).
  - Routes the query to the appropriate Sub-Agent (Expert Node).
  - Synthesizes the final answer.

## 3. Data Ingestion & Indexing (The Foundation)
To prevent retrieval pollution and context loss across complex documents (especially tables and hierarchical rules):
- **Document Parsing**: Advanced parsing (e.g., LlamaParse or Unstructured) to retain table structures and document hierarchies.
- **Metadata Tagging**: Strict labeling applied to all chunks injected into the Vector DB.
  - `category`: `[PDK | EDA | Project_Doc]`
  - `node`: `[N7 | N5 | ...]`
  - `tool`: `[Innovus | ICC2 | Calibre | ...]`
  - `project_id`: `[Proj_A | Proj_B | ...]`
- **Retrieval Pipeline**: All search operations execute hard metadata filters before vector similarity search, followed by a robust Reranker to surface the top chunks.

## 4. Expert Nodes (Sub-Agents)
The Supervisor routes requests to one of three specialized Expert nodes:
1. **PDK Expert (Pipeline)**
   - **Focus**: Process rules, DRC limitations, LVS setups, SPICE parameters.
   - **Behavior**: Pipeline-driven. Takes node parameters, performs exact metadata-filtered searches on PDK partitions, and summarizes. Emphasizes strict accuracy over generative reasoning.
2. **EDA Script Expert (Agent)**
   - **Focus**: Tool usage instructions, Tcl/Skill script generation.
   - **Behavior**: Agentic. Searches tool command reference manuals, generates scripts. Capable of multi-step loops (e.g., Generate -> Linter Check -> Refine).
3. **Metrics & History Analyst (Mixed)**
   - **Focus**: Project-specific metrics (PPA, timing convergence) and historical docs (Confluence, PPT).
   - **Behavior**: Uses standard RAG for project documents. Uses Text-to-SQL logic (via few-shot prompting) to query read-only Metrics databases for precise data extraction and reporting.

## 5. Technology Stack
- **Framework**: FastAPI, LangGraph, LangChain/LlamaIndex.
- **Models**: Cloud API models or robust Local Models (e.g., nemotron-3-super-120b-a12b-fp8) capable of tool calling and complex routing.
- **Vector Store**: Metadata-capable database (e.g., Milvus, Qdrant).
- **Reranker**: Compatible external or local reranker model.
