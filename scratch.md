### RAG 引用气泡与全文定位功能修改策略

根据对 `open-webui` (jbprag) 现有代码的分析，引用（Citation）的渲染流主要经过 `ContentRenderer.svelte` -> `MarkdownInlineTokens.svelte` -> `SourceToken.svelte` -> `Source.svelte`，而点击后弹出的右侧面板为 `CitationDrawer.svelte`。

要实现**悬停冒泡显示 Trunk (Chunk) 片段**、**气泡内含“查看来源”链接**以及**右侧弹窗展示全文并定位原文**的功能，建议按以下三个步骤进行修改：

#### 1. 后端/数据传递流改造：透传 Chunk 内容
目前 `ContentRenderer.svelte` 中的 `getSourceIds` 方法仅提取了引用的 `title` 或 `url` 并存入 `sourceIds` 数组，导致最末端的 `Source` 组件拿不到 Chunk 文本。
* **文件**: `src/lib/components/chat/Messages/ContentRenderer.svelte`
* **修改方法**: 将 `sourceIds` 的结构从 `string[]` 升级为 `object[]`。
  ```javascript
  const getSourceIds = (sources) => {
      const result = [];
      for (const source of sources ?? []) {
          for (let index = 0; index < (source.document ?? []).length; index++) {
              // 携带完整的 chunk 内容及元数据
              result.push({
                  name: metadata?.name || id,
                  chunkText: source.document[index], // Trunk/Chunk 的内容
                  metadata: metadata,
                  sourceId: id
              });
          }
      }
      // 注意：数组去重逻辑需要修改，根据对象的唯一标识（如 sourceId + chunkText）去重
      sourceIds = result; 
  };
  ```
同时，更新中间链路 (`Markdown.svelte`, `SourceToken.svelte`)，确保将这个对象作为 prop 传给 `Source.svelte`。

#### 2. 悬停气泡 (Tooltip) 及“查看来源”按钮实现
利用现有的 `Tooltip.svelte`（基于 tippy.js）来包裹引用标记 `[1]`，并开启交互模式 (`interactive=true`)，使得用户鼠标可以移入气泡内点击链接。
* **文件**: `src/lib/components/chat/Messages/Markdown/Source.svelte`
* **修改方法**:
  ```svelte
  <script lang="ts">
      import Tooltip from '$lib/components/common/Tooltip.svelte';
      export let sourceData; // 接收第1步传来的对象
      // ...
      $: chunkHtml = `
          <div class="flex flex-col gap-2 p-2 max-w-[300px] text-sm text-left">
              <div class="line-clamp-6 text-gray-200 break-words">
                  ${sourceData?.chunkText || '无内容'}
              </div>
              <!-- 点击时调用现有的 onClick(id) 唤起右侧 Drawer -->
              <button class="text-blue-400 hover:text-blue-300 hover:underline text-xs self-end mt-1 cursor-pointer" 
                      onclick="document.getElementById('source-btn-${id}').click()">
                  查看来源
              </button>
          </div>
      `;
  </script>

  <!-- 增加 interactive=true 允许鼠标进入气泡 -->
  <Tooltip content={chunkHtml} allowHTML={true} interactive={true} placement="top" className="w-fit">
      <button id="source-btn-{id}" class="text-[10px] text-blue-600 bg-blue-50/80 ..." on:click={() => onClick(id)}>
          <span class="line-clamp-1">[{index}]</span>
      </button>
  </Tooltip>
  ```

#### 3. 右侧弹窗 (CitationDrawer) 全文定位功能
目前 `CitationDrawer.svelte` 主要循环展示被检索到的多个 Chunk 片段。要实现“定位到原文，方便全文查看”，我们需要获取全文并在其中高亮 Chunk。
* **文件**: `src/lib/components/chat/Messages/Citations/CitationDrawer.svelte`
* **修改方法**:
  提供两种维度的实现方案：
  
  **方案 A（推荐，基于前端请求全文并滚动）**：
  1. 在 Drawer 展开且匹配到 `document.metadata.file_id` 时，向后端接口 `GET /api/v1/files/${file_id}/content` 请求文档全文。
  2. 拿到全文后，使用字符串查找（或正则）在全文中定位 `document.document` (即 Chunk 片段)。
  3. 渲染全文时，将该 Chunk 片段用 `<mark id="active-chunk" class="bg-yellow-200">` 包裹起来。
  4. 渲染完成后，利用 Svelte 的 `onMount` 或 `tick()`，执行 `document.getElementById('active-chunk').scrollIntoView({ behavior: 'smooth', block: 'center' })`。

  **方案 B（利用浏览器原生的 Text Fragment）**：
  现有代码中已经有 `getTextFragmentUrl` 方法可以生成形如 `#:~:text=fragment` 的 URL。
  如果不涉及复杂的排版解析，可以直接将 Drawer 内容区替换为 `<iframe>` 嵌入该文件的 API 地址：
  ```svelte
  <iframe 
      src={getTextFragmentUrl(document)} 
      class="w-full h-[80vh] border-0 rounded-lg bg-white"
  ></iframe>
  ```
  现代浏览器（如 Chrome/Edge）检测到 URL 中的 `#:~:text=` 时，会自动加载页面文本、滚动到对应位置并以黄色高亮背景标出 Trunk 的文字。
