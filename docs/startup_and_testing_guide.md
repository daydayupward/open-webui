# ChipRAG 启动与测试运行指南

本指南详细介绍了如何启动 PostgreSQL、准备/导入向量化数据、拉起 ChipRAG 代理后端及 Open WebUI 服务，完成整个物理设计问答系统的本地开发与联调测试。

---

## 1. 启动 PostgreSQL 数据库

由于检索底层依赖 `pgvector` 进行向量相似度匹配，且需要结构化数据库存储项目指标（PPA），建议使用带有 `pgvector` 插件的 PostgreSQL。

### 方式一：使用 Docker 启动 (推荐)
推荐运行官方的 `pgvector` Docker 镜像，能一键配置好所有插件与端口：
```bash
docker run --name pgvector \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=chip_design \
  -p 5432:5432 \
  -d pgvector/pgvector:pg16
```

### 方式二：使用 Linux/WSL 系统原生 PostgreSQL
如果您是在 WSL 或 Ubuntu 系统上原生安装了 PostgreSQL：
1. 启动数据库服务：
   ```bash
   sudo service postgresql start
   ```
2. 登录 postgres 控制台并创建对应数据库及安装 `pgvector` 扩展：
   ```bash
   sudo -u postgres psql
   # 在 psql 控制台中执行：
   CREATE DATABASE chip_design;
   \c chip_design
   CREATE EXTENSION IF NOT EXISTS vector;
   \q
   ```

---

## 2. 准备、注入样本数据 (Embedding Data Setup)

我们将使用内置的种子数据对向量数据库及指标数据库进行初始化。

1. 进入 `jbprag` 目录：
   ```bash
   cd jbprag
   ```
2. 确保已创建虚拟环境并安装所需依赖包：
   ```bash
   # 如果没有虚拟环境，执行创建：python3 -m venv .venv2
   source .venv2/bin/activate
   pip install -r requirements.txt
   ```
3. 检查 `.env` 文件中的配置，确保数据库连接串正确：
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/chip_design
   OPENAI_API_KEY=gpustack_your_key_here
   OPENAI_API_BASE_URL=http://10.1.88.119:8100/v1
   # 视觉模型配置
   VISUAL_API_BASE_URL=https://jmapi01.jaguarmicro.com
   VISUAL_API_KEY=your_key_here
   VISUAL_MODEL=gpt-5.4
   ```
4. 执行**数据注入脚本**，一键灌入 PDK 规则、EDA 手册、项目文档和 PPA SQL 指标：
   ```bash
   python3 scripts/seed_dev_data.py
   ```
5. 运行 pytest 确认全部后端组件与数据库通路运行正常：
   ```bash
   python3 -m pytest tests/
   ```

---

## 3. 拉起 RAG 代理服务 (jbprag backend)

在激活的虚拟环境下启动 `jbprag` 的 FastAPI 服务（监听 8000 端口）：
```bash
cd jbprag
source .venv2/bin/activate
uvicorn src.main:app --port 8000 --host 0.0.0.0 --reload
```

---

## 4. 启动 Open WebUI 服务

Open WebUI 采取前后端分离架构，开发调试时需要分别启动 Python 后端与 Vite 开发环境。

### 步骤 A：启动 Open WebUI 后端
1. 打开一个新的终端，进入 `backend` 文件夹：
   ```bash
   cd backend
   ```
2. 运行 `dev.sh` 脚本（将在 `8080` 端口开启后端，并自动载入 CORS 配置与安全密钥）：
   ```bash
   bash dev.sh
   ```

### 步骤 B：启动 Open WebUI 前端
1. 打开又一个新的终端，进入 root 根目录：
   ```bash
   cd ..
   ```
2. 运行 npm 启动 Vite 开发服务器（将在 `5173` 端口开启前端界面）：
   ```bash
   npm run dev
   ```

---

## 5. 前端功能测试与联调流程

服务拉起后，在浏览器中访问 **`http://localhost:5173`** 登录系统，执行以下验证流：

### 5.1 验证 RAG 后台管理面板
1. 点击左下角头像 -> 进入 `Admin Settings` (管理员设置)。
2. 在侧边栏菜单中，点击选择最下方的 `ChipRAG Admin`。
3. 验证管理面板各大板块功能：
   * **Ingestion**：尝试上传一份新 PDF 手册，观察 LLM 能否正确预检出分类、工具（Tool）等元数据并成功吸收入库。
   * **Catalog**：查看现存向量目录，确认种子数据对应的文档已入库。
   * **Versioning**：切换向量 Collection 版本，查看后端日志是否实现秒级热拔插。
   * **Traces**：向机器人提问后，在此页面刷新即可看到检索和幻觉判定 Trace 日志。

### 5.2 验证多模态 VLM 与 Self-RAG 对话
1. 回到 Chat 界面，创建一个新的对话。
2. 上传包含 DRC 报错或版图布局的截图，并在对话框中提问：
   > “分析这张图片中的 DRC 问题，查找对应的 PDK Rule 并给出设计建议。”
3. 检查系统表现：
   * 确认后端成功提取了图片中的层名或规则代号。
   * 观察 `jbprag` 控制台日志，确认触发了 **Self-RAG 流程**：
     * `grade_document_relevance` 判定召回手册与规则的真实关联度。
     * 发现不相关时是否触发了 `rewrite_query` 并重新发起 pgvector 检索。
     * 回答生成后是否通过了 `grade_hallucination` 幻觉校验。
   * 查看最终答复底部的 `参考来源`（Citations）能否精准定位到 PDF 文件的页码与出处。
