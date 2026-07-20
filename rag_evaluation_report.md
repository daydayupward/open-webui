# RAG 检索策略评估与 Chunking 优化方案报告

本报告对当前系统的 RAG 检索策略、LLM 遵循文档的严格程度、Chunk 长度现状进行了全面核对与评估，并提出了可行的 Chunking 策略优化方案。

---

## 一、 当前检索策略核对

经过对此前调试的评估，当前系统已建立起一套完整的多阶段 RAG 检索架构：
1. **多集合分发（Multi-Collection Dispatching）**：根据 Supervisor 路由分类，自动在 `pdk_rules`、`eda_manuals` 和 `project_docs` 之间并发检索，并基于 Qwen-Reranker 重新合并和精排。
2. **跨语言翻译与重写（Cross-lingual Query Rewriting）**：对于中文输入，首先重写翻译为英文术语，显著提升英文手册库（PDF）的向量检索召回率。
3. **图像专项检索（Targeted Image Retrieval）**：检测到图表诉求时，使用 SQL 在向量库中直接模糊查询包含 `/static/uploads/images/` 路径且包含目标技术词的 Chunk 进行前置强插。
4. **图像相似度评分加权（Image Score Boosting）**：对含图 Chunk 进行重排加分（+10.0），确保图表被优先输出。

---

## 二、 RAG 严格遵循文档评估

### 1. 约束机制
目前系统通过以下双重防护网确保 LLM 回答的严格程度：
* **Prompt 指引**：`EDA_SCRIPT_GENERATION_PROMPT` 与 `RESULT_SUMMARY_SYSTEM_PROMPT` 具有极强的严格性指示（如 `You MUST cite your facts using the numbered references... Every statement of fact derived from the context must have an inline citation.`）。
* **自适应 Self-RAG 评估与修正循环**：
  * 使用 `grade_hallucination` 判断回答是否 100% 被检索文档覆盖（Grounded）。
  * 使用 `grade_answer_completeness` 判断回答是否完整解答了用户提问。
  * 任何一项不通过，系统将进行最多 2 轮的 Refinement（反思修正）重试，直至通过或达到上限。

### 2. 评估结论
* **在文档召回正确时**：由于有严格的 Grounding Grader 和提示词约束，模型回答高度严谨，命令语法（Tcl）和流程步骤与原图文档高度契合。
* **在文档未召回时**：如之前因多轮对话中 Supervisor 解析 JSON 失败，进入 Fallback 导致 LLM 无 Context 生成。此时模型会依赖其预训练知识进行**幻觉回答**，出现虚假命令和假图片（如 `cts_flow_overview.png`）。
* **结论**：**RAG 严格度完全取决于检索文档的召回质量。**

---

## 三、 当前 Chunk 策略分析与评估

### 1. 现状：Chunk 片段过短且割裂
根据 [chunker.py](file:///home/eason/proj/open-webui/jbprag/src/ingestion/chunker.py) 源码：
* 系统采用 `_classify_blocks` 将文档拆分为 `header`、`table` 和 `paragraph`。
* 在构建 Chunk 时，**每个 Header（标题）、每个 Table（表格）和每个 Paragraph（段落）直接被 append 成为一个独立的 Chunk**，并未执行段落合并。
* **弊端**：
  1. **片段极其短小**：一个单独的 Header（如 `### Using the Mixed Placer`）仅 3-10 个 Token 却成为一个 Chunk；一句图片标记 `![](/static/uploads/images/xxx.png)` 也成为一个独立 Chunk。
  2. **上下文严重丢失（Disconnection）**：图片与描述文字、标题与正文段落在物理上是割裂的。向量模型检索时，往往只召回了包含文字的 Chunk，而包含图片的 Chunk 因为完全没有文字语义，相似度极低而丢失。
  3. **模型生成受限**：由于 Chunk 太碎，LLM 获得的是破碎的段落，难以拼凑出连贯的 Tcl 脚本。

---

## 四、 Chunking 策略优化空间与技术方案

为了解决 Chunk 片段过短且割裂的问题，建议进行以下三项优化：

### 📈 方案 1：基于 Header 的贪婪块合并（Greedy Block Merger）
* **做法**：不再单方面把每个 Paragraph 或 Header 作为独立 Chunk。而是以 Section 为基本单位，把处于同一 Heading 层级下的连续 Paragraph、列表、小表格进行**贪婪合并**，直至达到目标 Token 大小（如 500 - 800 Tokens）。
* **收益**：既保证了物理上的完整性（表格与上下文共存），又避免了超短 Chunk 带来的检索噪音。

### 🖼️ 方案 2：图文强绑定绑定机制（Colocated Image Binding）
* **做法**：在 Chunker 分类块时，如果发现某一行是 `![](/static/uploads/images/...)`，自动将其与前后的 `paragraph` 合并为一个 Chunk，强制**不允许分裂**。
* **收益**：图片 Chunk 与文字描述 Chunk 融为一体。检索到文字时，图片标记自然被一同带出，**不再需要目前额外的 SQL 关键词查图和强插补丁**，系统架构将更加干净和优雅。

### 🔗 方案 3：父子双粒度检索（Parent-Child / Hierarchical Chunking）
* **做法**：
  * **子 Chunk（Child）**：将大段落切成 150-200 Tokens 的小段，仅用于计算向量相似度（因为小片段在 Dense Retriever 中语义更聚焦，召回率更高）。
  * **父 Chunk（Parent）**：每个子 Chunk 都指向其所属的父 Chunk（800-1000 Tokens）。
  * **检索**：向量库检索到子 Chunk 后，在系统后台自动映射并取出其对应的**父 Chunk** 送给 LLM 进行理解和生成。
* **收益**：同时兼顾了“小颗粒度检索召回率高”与“大颗粒度理解上下文完整”的优势。

---

## 五、 总结

当前系统的 **检索架构** 与 **答题严格度控制** 均处于非常优秀的水平（有完整的翻译、重写、Rerank 和 Self-RAG 反思纠错闭环）。  
但底层的 **Chunking 策略存在明显缺陷**，片段过碎（Header 和图片链接单独成块）导致了极大的上下文割裂。  
**建议在下一阶段优先实现“方案 1（贪婪块合并）”和“方案 2（图文强绑定）”**，这将从底层根本上解决图文割裂与检索不全的问题。
