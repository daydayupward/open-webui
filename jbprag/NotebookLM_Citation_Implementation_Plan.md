# 实现 NotebookLM 风格的溯源与引用功能实现思路

要实现类似 NotebookLM 的引用溯源功能（包含行内引用 `[1]`、悬停弹窗预览、点击右侧边栏查看详细来源），需要**后端（Agentic RAG）**和**前端（Open WebUI）**两方面的配合。以下是具体的架构设计与实现思路：

## 1. 后端 (Agentic RAG / jbprag) 的改造思路

在目前的架构中，Agent 已经能够检索出文档，现在的核心是**强制模型输出引用标记**，并**提供对应的文档元数据**。

- **Prompt 改造**：在 `supervisor_prompt.py` 或问答 Prompt 中增加明确指令。要求大模型在引用上下文时，必须在对应的文本后加上引用角标（如 `[1]`, `[2]`）。
- **数据结构绑定**：
  - 组装给大模型的 Context 时，给每段 Chunk 一个清晰的编号：`[1] 来源: 某文件.md... 内容: ...`
  - 在返回给前端的 API Response 中，将这些 Chunk 的元数据（文档ID、文件名、摘要、甚至完整内容）统一放进 `citations` 或 `sources` 字段中（兼容 Open WebUI 的 metadata 扩展）。

## 2. 前端 (Open WebUI) 的改造思路

前端改造主要涉及**Markdown 渲染解析**、**交互式气泡卡片 (Popover/Tooltip)** 以及 **全局侧边栏 (Right Drawer)**。

### 2.1 行内引用标记的解析与渲染
- **定位代码**：Open WebUI 的 Markdown 渲染主要集中在前端的 `src/lib/components/chat/Messages/Markdown.svelte` 或相关的文本渲染组件中。
- **自定义解析**：使用正则表达式截获诸如 `[1]`、`[2]` 这样的引用标记，将其替换为一个自定义的 Svelte 组件 `<CitationBadge source={sourceData[1]} />`。

### 2.2 悬停气泡与点击弹窗 (Popover / Tooltip)
- **悬停交互**：在 `<CitationBadge>` 组件中，绑定 `on:mouseenter` 事件，或者使用 CSS/Tailwind 的 `group-hover`。展示一个小卡片（Popover）。
- **内容展示**：Popover 中展示来源文档的**标题**和**关键片段（Snippet）**。
- **操作按钮**：气泡底部放置一个类似于 “查看详情” 或 “查看源文件” 的按钮。

### 2.3 右侧边栏 / 侧拉窗口展示详细来源
- **状态管理**：在全局 Store 中维护一个状态（如 `activeSourceId` 和 `isSidebarOpen`）。当用户点击引用角标或悬停卡片中的“查看详情”时，触发侧边栏开启。
- **组件开发**：开发一个右侧滑出的侧边栏组件 `<SourceDetailDrawer>`。
- **功能特性**：
  - 侧边栏占据屏幕右侧一定比例，不遮挡主聊天界面。
  - 显示该 Chunk 对应的完整段落。如果有高亮功能，可以将匹配到的关键内容进行高亮渲染，方便核对。

## 3. 具体实施步骤与技术栈建议

### 第一阶段：后端引用打标对齐
- 修改大模型的 System Prompt，要求必须带有 `[1]` 等标记。
- 确保 API 返回的流式（Streaming）或非流式数据结构中，能附带一个 `docs: [...]` 的 JSON 结构，前后端通过角标 Index 建立映射关联。

### 第二阶段：前端悬停弹窗与引用解析
- 在 Open WebUI 中拦截大模型的回答文本，利用正则表达式或 Markdown 渲染插件，将 `[1]` 转换为交互式小红点或数字角标。
- 使用 `floating-ui` 或纯 CSS + Svelte 制作 Tooltip 悬停层。

### 第三阶段：右侧视图联动
- 在全局 Layout (`src/routes/+layout.svelte` 级别或 Chat Layout) 中引入一个 `Drawer` 侧边栏。
- 通过 Svelte Store 传递文档详情。实现点击后，右侧平滑展开并渲染 Markdown 格式的原文档信息。

---

> [!NOTE] 
> Open WebUI 本身其实已经内置了一套轻量级的 Citations 机制。我们可以**直接复用或魔改 Open WebUI 现有的文档展示逻辑**。
> 您是否希望我先帮您深入 Open WebUI 的前端代码，寻找出需要修改的具体文件并给出对应的代码修改计划？如果是，我将重点探查 `src/` 下关于 `Markdown` 渲染和 `Chat` 界面的代码。
