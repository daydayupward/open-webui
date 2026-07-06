# PDF/PDK 文档解析器评估与选型规格说明书

本说明书评估了各种 PDF 文本提取及结构化文档转换库在 **Jbpragic RAG System** 中的表现，并最终确立了后续的集成架构设计。

---

## 1. 背景与业务痛点
在芯片物理设计（后端）领域，输入 RAG 系统的 PDK 文档（例如 DRC/LVS 手册）以及 EDA 工具参考指南中包含大量的**高密度表格**（例如不同金属层 M1-M9 的 pitch、spacing 约束值）和**层级标题**。
由于现有的切分器 [chunker.py](file:///home/eason/proj/open-webui/jbprag/src/ingestion/chunker.py) 是基于 Markdown 语法（`#` 级联标题与 `|---|` 表格）实现的**结构化断句与不切断表格切分**，直接提取 PDF 原始无序文本流会导致以下问题：
1. 表格被拦腰截断或行列压扁，导致 LLM 在检索时无法对应层级与具体参数数值，精度急剧下降。
2. 多栏排版（Multi-column）文本拼接混乱，章节标题标识丢失，导致检索块（Chunks）的上下文 provenance 破损。

---

## 2. 解析器对比评估 (pypdf vs pdfplumber vs markitdown)

| 维度 | pypdf | pdfplumber | markitdown |
| :--- | :--- | :--- | :--- |
| **定位** | 基础 PDF 页面及纯文本操作 | 底层像素级几何坐标与网格分析 | 微软开源的多格式文档转 Markdown 工具 |
| **表格提取能力** | 极差（压扁为乱序文本，无行列对应） | **极强**（能基于线框或文字对齐自动抽取二维数组） | **强**（能开箱即用自动将表格渲染为 Markdown 语法表格） |
| **排版还原能力** | 差（多栏混合易出错） | 中（需要手工合并列文本） | **强**（自动转换为规范 Markdown，还原层级与大纲） |
| **支持的输入格式** | 仅 PDF | 仅 PDF | **多格式**（PDF, Word, Excel, PPT, HTML） |
| **依赖与运行开销** | 极轻量，纯 Python，速度极快 | 较重，解析坐标消耗内存大，速度较慢 | 较重，依赖多，速度视大模型 OCR 配置而定 |
| **与项目切片器契合度** | 差（需要大量二次开发） | 中（需要自行编写数组转 Markdown 表格代码） | **极强**（输出的 Markdown 语法与 Chunker 完美咬合） |

---

## 3. 设计决策与技术选型
1. **首选解析引擎：`markitdown`**
   * **理由**：能够把 PDF 和 Excel 转换成高质量的 Markdown。Markdown 表格（`| col |`）与 Chunker 的强力保护机制契合，能最大限度确保 PDK 规则表格以独立、完整的 Chunk 形式存储，极大提高 DRC Spacing 类查询的检索精度。
2. **辅选微调引擎：`pdfplumber`**
   * **理由**：对于极少数无表格线的隐式表，如果 `markitdown` 提取失败，开发人员可以基于 `pdfplumber` 精准抓取文本几何边界，在代码中二次序列化为 Markdown Table 格式导入。
3. **隔离解耦**：将 PDF/真实文档解析能力与 `src` 核心库解耦，通过独立的 `scripts/ingest_documents.py` 驱动。保持核心运行时轻量（不需要强装重量级 MarkItDown），确保现有单测与 Docker 构建快速稳定。

---

## 4. 数据流动与集成架构

```
+------------------+     (MarkItDown)     +--------------------+
| 真实 PDF / Excel  | -------------------> | IngestionDocument  |
| (PDK / Specs)    |                      | (Markdown Text)    |
+------------------+                      +--------------------+
                                                     |
                                                     v  (chunk_document)
+------------------+    (index_chunks)    +--------------------+
| PGVector 向量库  | <------------------- |    TextChunk 列表  |
| (pdk_rules 等)   |                      | (结构化分块)        |
+------------------+                      +--------------------+
```

所有提取的 Metadata 在分块后将被送入 `src.ingestion.metadata_mapper` 进行大类与子类规范化映射，统一字段后执行 SQL Upsert操作。
