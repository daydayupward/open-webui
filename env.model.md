# Chip-RAG 模型与多模态 API 配置指南 (env.model.md)

本文档整理了目前可用的 Embedding 模型、重排模型、主流大语言模型（LLM）以及多模态视觉模型（VLM）的 API 配置与切换选择指南。

---

## 1. 模型 API 信息一览

### 1.1 嵌入与重排模型 (Embedding & Rerank)
* **Embedding (bge-m3)**
  * 名称：`bge-m3`
  * 接口地址：`http://10.1.88.119:8100/v1` （域名：`http://jmaicloud.jaguarmicro.com:8100/v1`）
  * API Key：`gpustack_8a84577e7871ac6c_2c3d4ef8e376a5d2fca5ceb8e1cc4221`
* **Reranker (qwen3-reranker-8b)**
  * 名称：`qwen3-reranker-8b`
  * 接口地址：`http://10.1.88.119:8100/v1` （域名：`http://jmaicloud.jaguarmicro.com:8100/v1`）
  * API Key：`gpustack_8a84577e7871ac6c_2c3d4ef8e376a5d2fca5ceb8e1cc4221`

### 1.2 主流大语言模型 (LLM)
* **本地 GPUStack 托管版（默认）**
  * 名称：`nvidia-nemotron-3-super-120b-a12b-fp8` / `gpt-oss-120b`
  * 接口地址：`http://10.1.88.119:8100/v1` （域名：`http://jmaicloud.jaguarmicro.com:8100/v1`）
  * API Key：`gpustack_8a84577e7871ac6c_2c3d4ef8e376a5d2fca5ceb8e1cc4221`
* **JMApi 托管大参数版**
  * 名称（主流）：`deepseek-v4-pro` 或 `gpt-5.4`
  * 接口地址：`https://jmapi01.jaguarmicro.com`
  * API Key：`sk-4FdTM7qOGWDEKoO86FweSAbkANjnPlshni1kiHv3gTKj1rrZ`

### 1.3 多模态视觉大模型 (VLM - 用于识别 DRC 截图和文档图片描述)
* **gpt-image-2**
  * 名称：`gpt-image-2`
  * 接口地址：`https://jmapi01.jaguarmicro.com`
  * API Key：`sk-4FdTM7qOGWDEKoO86FweSAbkANjnPlshni1kiHv3gTKj1rrZ`

> [!TIP]
> **内网 DNS 无法解析提示**：如果 WSL 容器内遇到 `Could not resolve host: jmaicloud.jaguarmicro.com` 连接超时报错，请直接使用已静态解析的内网 IP 地址 `http://10.1.88.119:8100/v1`。

---

## 2. Chip-RAG 配置与模型选择方式

我们在 `chip_agent/src/settings.py` 中实现了配置字段，在 `chip_agent/src/utils.py` 中封装了模型选择器。您可以通过直接修改 [chip_agent/.env](file:///home/eason/proj/open-webui/chip_agent/.env) 文件完成模型切换：

### 2.1 主模型选择 (LLM Model Selection)
如果您希望使用高性能的 `deepseek-v4-pro` 或 `gpt-5.4` 作为回答生成主模型，只需在 `.env` 中修改注释状态：

```bash
# 切换为 JMApi 托管的 deepseek-v4-pro / gpt-5.4 示例：
OPENAI_API_BASE_URL='https://jmapi01.jaguarmicro.com'
OPENAI_API_KEY='sk-4FdTM7qOGWDEKoO86FweSAbkANjnPlshni1kiHv3gTKj1rrZ'
LLM_MODEL='deepseek-v4-pro'  # 或者是 'gpt-5.4'
```

### 2.2 视觉模型与图片支持 (VLM Model Configuration)
多模态视觉处理与图片描述提取由以下环境变量支持：

```bash
# 多模态视觉模型 API 配置 (用于运行图片识别与多模态转译)
VISUAL_API_BASE_URL='https://jmapi01.jaguarmicro.com'
VISUAL_API_KEY='sk-4FdTM7qOGWDEKoO86FweSAbkANjnPlshni1kiHv3gTKj1rrZ'
VISUAL_MODEL='gpt-image-2'
```

### 2.3 图片抽取与索引范围 (Image Ingestion Scope)
为了避免对纯代码等无意义的图表进行无谓的多模态描述，您可以通过修改 `.env` 中的类别过滤项来确定哪些文档分类在 Ingestion 入库时需要抽取图片并使用 VLM 识别：

```bash
# 图片索引抽取范围（逗号分隔的文档分类）
# 默认开启 PDK、StdCell、SRAM、IP 和 平台流程文档 的图片提取
IMAGE_INGESTION_CATEGORIES='PDK,StdCell,SRAM,IP,Platform_Flow'
```