# NotebookLM 风格引用与右侧边栏改造计划

经过对 Open WebUI 前端源码的深入探查，我们发现 **Open WebUI 已经内置了绝大部分您所要求的基础机制**（包括 Markdown 角标解析、悬停 Popover 气泡预览、以及点击后的弹窗）。
目前的痛点是：默认点击后是居中弹出的 `Modal` 弹窗，会遮挡主聊天区域。我们需要将其改造为类似 NotebookLM 的**右侧边栏（Right Sidebar / Drawer）**，同时在后端 Agent 中对齐这种数据格式。

## 发现与现状分析

1. **角标渲染与悬停 (Hover)**：
   - 文件：`src/lib/components/chat/Messages/Markdown/SourceToken.svelte`
   - 现状：代码第 48-77 行已经使用了 `bits-ui` 的 `LinkPreview` 组件，**实现了悬停时出现气泡（Popover）的功能**。
2. **点击响应 (Click)**：
   - 文件：`src/lib/components/chat/Messages/ResponseMessage.svelte`
   - 现状：代码第 852 行实现了 `onSourceClick` 回调，它会触发 `<Citations>` 组件的 `showSourceModal`。
3. **来源详情展示 (Modal)**：
   - 文件：`src/lib/components/chat/Messages/Citations/CitationModal.svelte`
   - 现状：这里使用了 `<Modal>` 居中弹出组件。这就是我们需要重点爆改的地方。

---

## 🛠 代码修改计划 (Implementation Plan)

### 阶段一：前端 UI 右侧边栏改造 (Open WebUI)

目标：将原本居中的 `<Modal>` 替换为从右侧平滑滑出的侧边栏 `<Drawer>` 或定制化的全高侧边栏。

#### [MODIFY] `src/lib/components/chat/Messages/Citations/CitationModal.svelte`
- **改动点**：
  - 移除原有的 `<Modal>` 标签包裹。
  - 替换为从右侧固定 (`fixed right-0 top-0 h-full w-[400px] shadow-xl bg-white dark:bg-gray-900 transform transition-transform duration-300 z-50`) 滑出的侧边栏 DOM 结构，利用条件渲染类如 `translate-x-0` 和 `translate-x-full` 实现划入划出动画。
  - 保留并美化内部的 Markdown 渲染逻辑和 Relevance 打分逻辑。
  - 增加一个“关闭”按钮（`XMark`）固定在左上角或右上角。
  - 增加一个半透明的遮罩层（Overlay），点击遮罩层也可以关闭右侧边栏。

#### [MODIFY] `src/lib/components/chat/Messages/Citations.svelte`
- **改动点**：
  - 此文件负责挂载 `CitationModal`。交互逻辑（`showCitationModal = true`）不需要大动，但我们需要将其调整为不再居中遮挡内容。如果有必要，我们将 `CitationModal` 重命名为 `CitationDrawer` 以符合语义。

#### [MODIFY] `src/lib/components/chat/Messages/Markdown/SourceToken.svelte` (可选优化)
- **改动点**：
  - 目前的悬停气泡样式比较基础，我们可以给 `LinkPreview.Content` 的样式进行微调，让它的 UI 更加像 NotebookLM 的气泡质感（如圆角、阴影、截断字数优化等）。

---

### 阶段二：后端 Agent 格式对齐 (chip_agent)

目标：为了让 Open WebUI 触发上述逻辑，后端必须返回符合它期望的数据格式。

#### [MODIFY] `chip_agent/src/graph.py` (及相关的 RAG 组装节点)
- **改动点**：
  - **Prompt 注入**：强行规定模型回答时必须在引用的事实后添加 `[1]`、`[2]` 角标。
  - **组装 Context**：提供给大模型的检索文本必须被编号。
    ```text
    [1] 来源: pdk_docs/guide.pdf
    内容: xxxx
    ```

#### [MODIFY] `chip_agent/src/streaming.py` 或 API 包装层
- **改动点**：
  - 在返回给 Open WebUI 的 `/v1/chat/completions` API 响应中，在最终或第一个 Chunk 中注入 `citations` 数组元数据。
  - 数据结构需要契合 Open WebUI 期待的格式：
    ```json
    {
      "message": { "content": "..." },
      "citations": [
        {
          "source": { "name": "pdk_docs/guide.pdf" },
          "document": ["原文本内容片段..."],
          "metadata": [{ "page": 12, "file_id": "xxx" }]
        }
      ]
    }
    ```

## 用户确认

> [!IMPORTANT]
> 1. 您是否希望我直接开始在 Open WebUI 中修改 `CitationModal.svelte` 的代码，将其重写为右侧滑出的侧边栏？
> 2. 我稍后会将此计划文件拷贝至您的 WSL 项目路径中。
> 请点击下方 Proceed 确认，我们将直接开始前端部分的侧边栏代码改造！
