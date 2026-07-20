# ChipRAG 调试与功能验证测试问题集

在系统本地拉起并完成 `innovus_cui` 手册（`innovusUG`、`innovusTCR`、`DBcom`）的向量摄取后，您可以使用本问题集进行功能调试与 RAG 检索校验。

> **💡 调试启动提示信息 (Default Debug Prompt)**
> 
> 在启动或空负载调试时，系统默认提示语为：
> `I am ready to assist. Please let me know how I can help with your physical design query.`

---

## 1. 基础命令语法与选项测试（针对 `innovusTCR`）
* **测试问题 1**：
  > “在 Innovus 25 的 Common UI (CUI) 中，关于 `editPin` 命令放置引脚时，如何指定引脚在特定的层（layer）和边界位置（side）？请给出命令格式和具体示例。”
* **测试问题 2**：
  > “在 CUI 中，使用 `set_db` 和 `get_db` 调整设计的 Placement 密度或控制 row 属性时，有哪些常用参数？如何查询当前的 placement status？”

## 2. Common UI 流程与新旧命令对比测试（针对 `innovusUG`）
* **测试问题 3**：
  > “在 Innovus Common UI (CUI) 流程中，传统的 `dbGet` 命令在抓取设计对象属性时被如何替代？如何使用全新的 `get_db` 命令来获取某个 instance 的所在坐标（location）及朝向（orient）？”
* **测试问题 4**：
  > “请问在 25 版本的 Innovus CUI 流程中，进行多拐角多模式（MMMC）时钟树综合（CTS）和时序优化的标准流程和主要步骤是什么？”

## 3. 数据结构抓取与高级 Tcl 脚本编写测试（针对 `DBcom`）
* **测试问题 5**：
  > “根据 DBcom 手册的数据抓取逻辑，请帮我写一段 TCL 脚本：遍历设计中所有的 Net，找出其中引脚数（Pin count）大于 10 的 Net 名称，并输出它们连接的实例（Instance）名称。”
* **测试问题 6**：
  > “在 DBcom 数据库结构中，`dbBBox`（边界框）的数据是如何表示的？如何通过 DBcom 命令抓取并计算某个 Instance 内部某个特定 Pin 的物理中心点坐标？”

## 4. 图像语义与拓扑建模测试（针对 VLM 插图检索）
* **测试问题 7**：
  > “在 DBcom 的数据库建模中，Instance（实例）、Cell（单元）、Pin（引脚）、Net（网线）和 Term（终端）之间的连接与层级拓扑关系是怎样的？它们在数据库内部是如何相互引用的？”
* **测试问题 8**：
  > “参考设计手册中的图示，解释在物理设计中，Block 的 Row 结构与 Site 之间的对齐关系，以及它是如何影响 Standard Cell 放置的？”
o