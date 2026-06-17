# PDF 水印与页边距清理清洗器设计规格说明书

本说明书确立了在 **Chip Agentic RAG System** 中针对 PDF 格式的文档（如 timing/PDK specs）进行页眉页脚裁剪和水印物理擦除的设计规范，整合了基于像素坐标裁剪与特定内容擦除的物理清除方案，并规定了相关的独立评估对比工具的实现机制。

---

## 1. 业务背景
在芯片物理设计中，绝大多数手册及项目规格书都为高度机密文件，页面上带有大量斜角倾斜的文字水印（如 `"CONFIDENTIAL"`）或保密电子图章，并且在页面四周印有页眉页脚（如 `"Page X of Y"` 或 `"TSMC NDA REQUIRED"`）。
直接解析提取会导致：
1. **语义割裂**：页眉页脚文字插入到页面顶底部的表格或段落中间，导致 Markdown 表格解析变形。
2. **向量污染**：高频出现的水印词严重干扰向量匹配度计算。

---

## 2. 核心技术设计

本系统采用 **对象物理擦除（PyMuPDF） + 物理范围涂白裁剪（Margin Redaction） + 文本正则后处理（Regex Clean）** 的联合防线方案。

### 2.1 PyMuPDF 物理去水印与页边距裁剪
* **图章物理擦除**：通过遍历 `page.annots()`，检测 `annot.type[0] == 8`（代表 Stamp 图章类型注释），并执行 `page.delete_annot()` 擦除绝大多数电子水印。
* **物理边距涂白擦除**：通过获取页面的高度 `page.rect.height` 和宽度 `page.rect.width`：
  - 构建页眉区域矩形：`fitz.Rect(0, 0, width, header_margin)`。
  - 构建页脚区域矩形：`fitz.Rect(0, height - footer_margin, width, height)`。
  - 调用 `page.add_redact_annot()` 涂白覆盖上述边距区域，再执行 `page.apply_redactions()`，从 PDF 二进制层物理彻底删除边距内的字符和图像。这能从物理层规避页眉页脚被切片器读取，保障正文的连续性。
  - 针对斜角水印（如 `CONFIDENTIAL`），使用 `page.search_for()` 搜索该词并对其所在矩形区域执行 Redaction 物理擦除。

### 2.2 文本正则后处理 (Regex Post-processing)
通过 `markitdown` 提取出文本后，使用正则表达式进行兜底过滤（主要为了清除没有成功被物理擦除或散落在正文中的保密说明语句）。

---

## 3. 脚本工具设计

### 3.1 物理清理工具 [clean_pdf.py](file:///home/eason/proj/open-webui/chip_agent/scripts/clean_pdf.py)
* **功能**：独立执行 PDF 文件去水印和裁剪。
* **输出**：生成一个物理干净的新 PDF，文件名为 `[original_name]_cleaned.pdf`，用于可视化校验正文是否被切除。

### 3.2 提取文本对比工具 [compare_pdf_clean.py](file:///home/eason/proj/open-webui/chip_agent/scripts/compare_pdf_clean.py)
* **功能**：对两份 PDF 文件提取文本，进行 Diff 对比。
* **展示效果**：在终端打印原始提取文本与清洗后提取文本的前 N 页（默认前 3 页）的差异。
  - 被清除的水印行以 `-` 标识（代表已物理剔除）。
  - 正文变动（如果有）以差异标识呈现。

### 3.3 主导入流水线集成 [ingest_documents.py](file:///home/eason/proj/open-webui/chip_agent/scripts/ingest_documents.py)
* **参数**：增加 `--clean` 选项启用清洗流，默认 `--header-margin 50`，`--footer-margin 60`。
* **工作流**：
  1. 如果 `--clean` 为 True，调用 `clean_pdf.py` 内部逻辑生成 `temp_clean_[random].pdf`。
  2. 将该临时 PDF 喂给 `MarkItDown` 进行转换。
  3. 获取 Markdown 字符串后，调用文本正则过滤器做后置兜底过滤。
  4. 最终完成分块切分与索引后，在 `finally` 块中执行 `os.remove()` 彻底销毁该临时 PDF。
