# Workspace Customizations

## Rules
- When generating artifacts (e.g., implementation plans, summaries, reports), always output them directly to the project workspace directory (e.g., `\\wsl.localhost\Ubuntu\home\eason\proj\open-webui\...`) instead of the default Windows AppData path. Provide standard Markdown links to these WSL paths so the user can easily open them in their editor.
- **RAG Metadata Filtering Rules**:
  - Do not apply project-specific metadata filters (e.g., `project_id`) when querying or retrieving general platform or flow categories (e.g., `Platform_Flow`, `PDK`, `StdCell`, `SRAM`, `IP`, `EDA`, `Script`, `Literature`).
  - Project-specific metadata filters should strictly be restricted to project-specific categories (e.g., `Project_Doc`).
  - Normalize any platform names (like `"jbp"`) to `None` in the query's `project_id` to prevent it from restricting retrieval on platform documents.

- **Cross-Lingual Manual Retrieval Rules**:
  - When querying English manuals using Chinese, always translate or rewrite the query to English search terms before performing the first vector search retrieval. This ensures optimal recall.
  
- **Short-Text Image Chunk Retrieval Rules**:
  - Dense embedding models have low recall for short chunks that only contain image/diagram references (e.g. `![](/static/uploads/images/...)`).
  - When a query asks for diagrams, flowcharts, or illustrations, explicitly search the database (using SQL/keyword matching on terms like `placer`, `mesh`, `pillar` etc.) for image-containing chunks and prepend them to the candidate pool before reranking.
  - Boost the score of these image chunks by a set threshold (e.g., +10.0) during reranking to prioritize them in generation.

- **LangGraph Event Citation Rules**:
  - Ensure that event streaming logic (e.g. in `streaming.py`) captures events from all graph levels (including `__root__` and sub-graphs like `LangGraph`), so that document sources and citation metadata are correctly captured and yielded to the client.

