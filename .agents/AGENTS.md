# Workspace Customizations

## Rules
- When generating artifacts (e.g., implementation plans, summaries, reports), always output them directly to the project workspace directory (e.g., `\\wsl.localhost\Ubuntu\home\eason\proj\open-webui\...`) instead of the default Windows AppData path. Provide standard Markdown links to these WSL paths so the user can easily open them in their editor.
- **RAG Metadata Filtering Rules**:
  - Do not apply project-specific metadata filters (e.g., `project_id`) when querying or retrieving general platform or flow categories (e.g., `Platform_Flow`, `PDK`, `StdCell`, `SRAM`, `IP`, `EDA`, `Script`, `Literature`).
  - Project-specific metadata filters should strictly be restricted to project-specific categories (e.g., `Project_Doc`).
  - Normalize any platform names (like `"jbp"`) to `None` in the query's `project_id` to prevent it from restricting retrieval on platform documents.
