# 多模态 RAG (MM-RAG) 图片上传与 Tag 提取功能 (v0.2) 实施计划

本计划旨在完成用户要求的多模态 RAG (v0.2) 核心功能：当用户在界面上传图片或截图时，系统能够接入视觉大模型 (VLM)，自动对图片进行分析、识别报错或图示细节（提取 Image Tag），并无缝对接到后续的向量检索（Screenshot-to-DRC RAG）和最终的文本/图文回答生成流程中。

## User Review Required

> [!IMPORTANT]
> 1. **大模型兼容性依赖**: 开启此功能后，负责提取和生成的 LLM 必须支持多模态请求。当前系统配置了 `get_visual_llm`，我们将确保在检测到用户发送图片时，Supervisor 自动切换到视觉模型（如 `gpt-image2`）来提取 Tag。
> 2. **数据结构变更**: 现有的 `api_models.py` 假设用户的 `content` 只是一个字符串。我们必须将其变更为 `Union[str, List[Dict[str, Any]]]` 才能兼容 OpenAI 的多模态协议。

## Open Questions

> [!WARNING]
> 1. 前端向 `/v1/chat/completions` 发送多模态请求时使用的是标准 OpenAI API 格式（`image_url`），我们确认这样处理并在 Metadata 中注入 `image_tags` 是否符合你的预期？

## Proposed Changes

### 1. 基础模型升级 (API Models)

#### [MODIFY] [api_models.py](file:///home/eason/proj/open-webui/jbprag/src/api_models.py)
- 将 `ChatMessage` 类中的 `content: str` 修改为 `content: Union[str, List[Dict[str, Any]], Any]`，允许接收多模态消息体。

### 2. 消息流转工具 (Message Utils)

#### [MODIFY] [message_utils.py](file:///home/eason/proj/open-webui/jbprag/src/message_utils.py)
- 更新 `openai_to_langchain`：当 `content` 为 List 时，原样将其放入 `HumanMessage(content=...)` 中，保留多模态信息。
- 新增 `extract_text_from_message(msg: AnyMessage) -> str` 辅助方法：如果消息内容是 List，自动抽取出 `type == "text"` 的部分合并返回，确保无法处理图片的老代码仍能拿到文本。
- 新增 `has_image_in_messages(messages: List[AnyMessage]) -> bool` 辅助方法，用于快速判断请求是否包含图片。

### 3. 路由与图片 Tag 提取 (Supervisor)

#### [MODIFY] [supervisor.py](file:///home/eason/proj/open-webui/jbprag/src/supervisor.py)
- 修改 `arun_supervisor`，增加多模态分支逻辑：
  - 如果 `has_image_in_messages(all_messages)` 为 True，则动态调用 `get_visual_llm(temperature=0.0)`，否则仍使用普通的 `get_llm()`。
  - VLM 除了输出原有的 Metadata JSON 外，还需要输出新增的 `image_tags` 字段。
- 将提取出的 `image_tags` 合并保存到 `state["metadata"]["image_tags"]` 中。

#### [MODIFY] [supervisor_prompt.py](file:///home/eason/proj/open-webui/jbprag/src/prompts/supervisor_prompt.py)
- 在 JSON schema 约束中，为 `metadata` 增加一项 `"image_tags": "string (If the user uploaded an image, provide a detailed description of the design, schematic, or DRC violation shown. Otherwise null.)"`。
- 在 Prompt 指令中补充要求：如果用户上传了截图，仔细识别界面、提取报错名称、坐标和数值，并将这些信息填入 `image_tags` 作为后续数据库的检索扩充词。

### 4. 检索层适配 (Expert Retrievers)

#### [MODIFY] [pdk_expert.py](file:///home/eason/proj/open-webui/jbprag/src/experts/pdk_expert.py) 
- 使用 `extract_text_from_message` 来获取用户的纯文本 `query`。
- 提取 `state["metadata"].get("image_tags")`，如果存在且不为空，则拼接到 `query` 的末尾（例如：`query = query + "\n\n[附图片解析信息用于增强检索]:\n" + image_tags`）。
- 其他所有专家（如 `eda_script_expert.py`, `metrics_analyst.py`）同步应用该查询文本提取和 Tag 拼接修改。

## Verification Plan

### Automated Tests
- 编写或更新针对 `api_models.py` 和 `message_utils.py` 的测试用例，确保传入多模态 `List[Dict]` 不会崩溃。

### Manual Verification
1. 启动服务，发起一次带有 base64 图片或 URL（如截图）的请求。
2. 确认 `arun_supervisor` 调用了 `gpt-image2`，并在 `metadata` 中正确提取出 `image_tags`。
3. 确认拼接了 Tag 的纯文本 `query` 成功被 `pdk_retriever` 消费并用于检索。
