# Open-WebUI 本地开发与测试启动指南

为了方便您在修改代码后进行本地测试和查阅，以下是完整拉起 Open-WebUI 前后端服务的步骤指南。

## 1. 启动后端服务 (Backend)
后端使用 Python FastAPI，依赖于项目的 `.venv` 虚拟环境。

打开一个**新的终端窗口**，执行以下步骤：

```bash
# 1. 进入项目根目录
cd /home/eason/proj/open-webui

# 2. 进入 backend 目录
cd backend

# 3. 激活虚拟环境
source .venv/bin/activate

# 4. 启动后端服务
bash start.sh
```
*(注：如果 `start.sh` 无法直接运行，您也可以直接执行 `uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --reload` 来开启热更新调试)*

---

## 2. 启动前端服务 (Frontend)
前端使用 SvelteKit 和 Vite 驱动。

打开**另一个新的终端窗口**，执行以下步骤：

```bash
# 1. 进入项目根目录
cd /home/eason/proj/open-webui

# 2. 启动前端开发服务器
npm run dev
```
*(此命令将在本地开启一个带热重载的开发服务器，通常运行在 `http://localhost:5173` 或类似端口)*

---

## 3. 启动 Jbprag 服务 (可选)
如果您的测试涉及到独立的 Jbprag 代理功能，您还需要拉起此服务。该服务也有独立的虚拟环境。

打开**第三个新的终端窗口**，执行以下步骤：

```bash
# 1. 进入项目根目录
cd /home/eason/proj/open-webui

# 2. 进入 jbprag 目录
cd jbprag

# 3. 激活虚拟环境
source .venv/bin/activate

# 4. 启动 FastAPI 代理服务
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
*(此服务通常运行在 `http://localhost:8000`)*

---

## 4. 测试与验证
1. 打开您的浏览器，访问 `http://localhost:5173`。
2. 在任意对话中触发 RAG 检索（例如上传一个文档并询问相关问题）。
3. 当 AI 生成包含引用 `[1]` 的回答时，测试我们刚刚加入的悬停气泡和点击效果：
   - **悬停测试**：鼠标悬停在 `[1]` 上，确认气泡正常弹出且能正确展示长段落。
   - **跳转测试**：点击气泡内的**“查看来源”**或直接点击 `[1]`，确认右侧抽屉（Drawer）弹出。
   - **全文查看测试**：确认抽屉成功渲染了原文的 Full-text，带有 `<mark>` 高亮背景，并且在打开的瞬间是否自动平滑滚动到了该高亮区域。

> **提示**：如果发现修改没有立刻生效，可以检查是否保存了文件、重启了一次前端开发服务器，或在浏览器中执行强制刷新 (Ctrl+F5 或 Cmd+Shift+R) 以清理缓存。
