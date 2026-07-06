# 芯片后端 Agentic RAG 系统实施计划 (Implementation Plan)

## 阶段一：底层基础设施与数据管道建设 (Week 1 - 2)
**目标：** 完成“弹药库”建设，跑通离线多模态数据解析管道。

* **Task 1.1 环境与存储初始化**
    * 部署向量数据库（推荐 Milvus 或 Qdrant，需支持稠密向量与稀疏向量混合存储）。
    * 配置文件系统/对象存储（S3/MinIO），用于存放裁剪后的 DRM 原图。
* **Task 1.2 版面分析与预处理引擎开发**
    * 集成并微调视觉文档解析模型（LayoutLMv3 或 YOLOv8-Doc）。
    * 编写脚本对样例 Foundry PDK PDF 进行自动化切割，提取段落、表格、图片 BBox。
* **Task 1.3 核心清洗组件开发**
    * **表格转 Markdown 模块：** 确保规则表映射准确率达标。
    * **VLM Captioning 模块：** 调用 API（如 GPT-4o-vision 或 Gemini 1.5 Pro）批量为裁出的图片生成物理语义 Metadata。
* **Task 1.4 复合 Chunk 组装与入库**
    * 开发数据组装脚本，将 `[标题 + 文本 + 表格 + 图片 Metadata]` 绑定生成 Chunk ID，完成首批测试数据的向量化与入库。
    * **里程碑 1：** 随机抽查 50 个高难度规则，人工验证复合 Chunk 知识没有发生图文错位。

## 阶段二：在线混合检索引擎开发 (Week 3)
**目标：** 完成“精准雷达”，打通双路召回与融合重排链路。

* **Task 2.1 提问特征多维提取器开发**
    * 开发前端接收接口（支持 Text + Image）。
    * 开发视觉流提取器：调用 VLM 对用户的 Layout 截图生成结构化特征描述。
* **Task 2.2 三路召回引擎对接**
    * 实现 Dense Vector Search (语义提取)。
    * 实现 BM25 倒排索引匹配 (解决硬编码规则召回)。
    * 实现 Visual-Metadata 匹配。
* **Task 2.3 Reranker 与上下文组装**
    * 集成多模态 Rerank 模型，编写加权打分脚本（可配置权重参数）。
    * 编写 Prompt Assembler，设置 Token 截断阈值，组装最终的跨模态上下文。
    * **里程碑 2：** 使用 20 个真实的图文混排提问进行 Retrieval 测试，确保 NDCG@3 指标 > 85%。

## 阶段三：Agent 路由与 Coder 防御回路开发 (Week 4 - 5)
**目标：** 实现系统的大脑，彻底解决 Tcl 脚本生成的幻觉问题。

* **Task 3.1 基础路由与 QA Agent 构建**
    * 使用 LangChain / LlamaIndex 搭建底层 Agent 状态机。
    * 开发 Router Agent 意图识别模块。
    * 对接 QA Agent，完成纯规则查询闭环。
* **Task 3.2 Coder Agent 环境与第一、第二防御层建立**
    * **字典工具 (Tool 1)：** 将 Innovus/Calibre Command Reference 转化为本地查询工具（JSON 字典库），供 Agent 调用。
    * **Few-Shot 工具 (Tool 2)：** 收集 50-100 个历史高质量 Golden Scripts，入库并建立相似度检索分支。
* **Task 3.3 轻量 Linter 沙盒与反思机制 (核心攻坚)**
    * 使用 Python 开发/引入轻量级 Tcl 语法树解析器 (AST Linter)。
    * 编写 Self-Reflection 逻辑：设定最大重试次数为 3 次，将 Linter 的 Error Log 转换为 Prompt 打回给 Coder Agent。
    * **里程碑 3：** 运行 30 个自动化修线脚本生成任务，确保命令幻觉率降至 0%，语法通过率达到 100%。

## 阶段四：兜底机制、监控看板与上线部署 (Week 6)
**目标：** 打造工业级健壮性，确保极端情况安全降级。

* **Task 4.1 异常处理与降级机制开发**
    * 编写针对“图像极度模糊”、“零召回”、“反思死循环”的特定 Fallback 提示词和中断逻辑。
    * 实装“人工介入 (Human-in-the-loop)”高亮标记功能。
* **Task 4.2 API 封装与前端联调**
    * 打包后端 FastAPI / gRPC 服务，明确输入输出 Schema。
    * 与内部工作流 UI（或终端命令行 CLI）进行对接联调。
* **Task 4.3 效能大屏与埋点日志**
    * 完成对 Token 消耗、生成延迟、反思重试次数、脚本可执行率的数据埋点。
    * 配置基础监控 Dashboard。
    * **里程碑 4：** 系统 Alpha 版发布，邀请 3-5 名核心 PD 工程师开展第一轮灰度测试 (Dogfooding)。