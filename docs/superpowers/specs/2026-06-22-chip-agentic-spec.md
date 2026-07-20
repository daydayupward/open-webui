# 芯片后端设计 Agentic RAG 系统架构设计文档 (Design Spec)

**文档状态:** 已审核 (Approved)
**核心架构路线:** 方案 2（定制化多智能体 + 图文双路召回 RAG + 沙盒防御回路）
**目标领域:** 芯片物理设计 (Physical Design) / EDA 脚本生成与 DRC 规则问答

---

## 模块一：离线多模态数据解析管道 (Offline Data Ingestion)

本模块负责将非结构化、图文交织的官方 Foundry PDF（如 DRM、PDK 手册）转化为系统可读的“复合知识块”，彻底解决传统 RAG 的图文割裂问题。

### 1. 核心组件
* **版面分析器 (Layout-Aware Parser):** 采用视觉目标检测模型（如 LayoutLMv3/YOLOv8-Doc），精准提取 PDF 中的段落 BBox、标题 BBox、图像 BBox 与表格 BBox。
* **表格结构化引擎 (Table Extractor):** 将后端极其复杂的 DRC 规则表（如宽金属间距跳变表）精准解析为结构化的 Markdown 格式，保留严格的行列映射关系。
* **视觉语义生成器 (VLM Captioner):** 调用轻量级多模态模型对剥离出的官方 DRC 示意图进行预处理，生成“物理拓扑特征描述”（如：“展示了 Via1 在 M1 上的最小覆盖约束”），并作为 Metadata 存储。
* **复合 Chunk 绑定引擎 (Composite Chunking):** 将“父级标题 + 文本规则 + Markdown 表格 + 示意图及其 Metadata”打包为不可分割的联合单元，存入向量数据库与对象存储。

---

## 模块二：在线多模态 RAG 检索引擎 (Online Retrieval Engine)

本模块负责在前端接收到用户的图文混合输入（如版图报错截图 + 提问）后，精准命中并召回对应的官方规则规范。

### 1. 多维特征实时提取
* **文本流:** 提取提问关键词（Layer、Rule Type、Tool），生成 Dense Embedding。
* **视觉流:** 激活 VLM 提取物理截图特征（报错区域高亮、颜色代表的金属层、线宽拓扑），生成结构化视觉描述。

### 2. 多路混合召回与融合重排
* **三路并发召回:**
  1. 文本语义检索 (Dense Vector Search)
  2. 关键词精确匹配 (BM25 Search，确保 `M1.S.1` 等硬编码不漏搜)
  3. 视觉语义检索 (利用截图提取的视觉特征去匹配离线入库的官方图 Metadata)
* **跨模态融合重排 (Reranker):** 通过打分公式 `Score = α*(Text_Score) + β*(Visual_Score)`，对三路召回的候选块进行综合排序。
* **多模态 Prompt 组装:** 将得分最高的 Top-K 复合知识块（含官方图、Markdown 表格、文本）与用户截图打包，注入大模型上下文。

---

## 模块三：多智能体协作与 Coder Agent 防御回路 (Agentic & Defense Loop)

本模块是系统的“大脑与双手”，负责任务编排与零幻觉的代码生成。

### 1. 路由与拆解层
* **Router Agent:** 根据输入意图，将流量分发至 QA Agent（纯问答）、Data Agent（查 PPA 指标）或 Coder Agent（写脚本）。
* **Planner Agent:** 针对复合任务（如看图查违例并写脚本），拆解步骤并协调各个专职 Agent 串行工作。

### 2. Coder Agent 三层防御回路 (防幻觉核心)
为了确保生成的 Innovus/Calibre Tcl 脚本 100% 可执行：
* **第一层：EDA 语法字典强校验:** 写代码前强制调用 `search_eda_command` 工具，获取官方最新命令与 Flag 参数（如 `editMove -nets`），杜绝大模型凭空捏造。
* **第二层：Golden Script Few-Shot 注入:** 自动检索知识库中相似的资深工程师历史脚本（包含 Error Catch 机制），作为范例注入 Prompt。
* **第三层：本地 Linter 沙盒与自我反思 (Self-Reflection):** 脚本生成后，后台 Python Tcl-Linter 进行轻量级语法树校验。若遇括号未闭合或参数错误，打回给 Agent 进行最多 3 次的反思重写，直至校验通过才向用户输出。

---

## 模块四：系统异常处理、性能边界与评价指标 (Reliability & Metrics)

本模块定义了系统的下限防护与效果度量标准。

### 1. 异常降级策略 (Graceful Degradation)
* **截图极度模糊/缺失:** 挂起检索流，主动向用户发起反问，要求补充具体的 Layer 和线宽文字说明。
* **Linter 陷入反思死循环:** 达到 3 次重试上限后停止，输出当前 Best-effort 脚本并高亮报错行，提示需“人工复核 (Human-in-the-loop)”。
* **知识库零召回:** 触发安全回复拦截机制，输出“未检索到相关工艺规则”，严禁编造理论。

### 2. 核心评价指标 (KPIs)
* **一次性执行通过率 (First-Time Executability):** Coder Agent 生成的代码未经修改直接在工具中跑通的比例（目标：> 85%）。
* **命令幻觉率:** 捏造的 EDA 命令或非法参数比例（目标：严格压制为 0%）。
* **多路图文召回准确率 (NDCG@3):** 前三条召回的图文块包含正确修复规则的比例（目标：> 90%）。