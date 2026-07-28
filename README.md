# 建筑设计规范知识模型

本项目读取 `规范数据集/` 中的建筑设计规范 CSV，将条文导入 SQLite，并通过 OpenAI 兼容 LLM API 自动抽取可审核的实体、关系和约束规则，最终以交互式知识模型展示。

## 快速开始

```powershell
cd backend
pip install -r requirements.txt
Copy-Item .env.example .env
# 编辑 .env，填入 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
python import_internal_data.py
python app.py
```

另开一个终端：

```powershell
cd frontend
npm install
npm run dev
```

打开前端后，进入“规范库”选择一份规范，在条文页面点击“LLM 标注”。模型输出会先作为待审核标注保存；在确认原文证据后点击“审核通过并写入图谱”。“知识模型”页面可筛选、搜索、导出，并在点击节点时显示条文证据。

## LLM 配置

后端调用 `{LLM_BASE_URL}/chat/completions`，使用标准 Bearer Token，因此可配置 OpenAI、DeepSeek、通义千问兼容网关或企业内部兼容网关。密钥只放在 `backend/.env`，不要提交到版本库。

## Docker 部署

安装 Docker Desktop（本机）或在云服务器安装 Docker 后，在项目根目录执行：

```powershell
Copy-Item .env.example .env
# 编辑 .env：至少设置 SECRET_KEY；需要 LLM 标注时再设置 LLM_API_KEY
docker compose up --build -d
```

检查服务：

```powershell
docker compose ps
curl http://127.0.0.1:5000/api/health
```

访问 `http://服务器地址:5000`。数据会保存在 Docker 命名卷 `knowledge_data`；生产部署应在反向代理中配置 HTTPS，并将密钥保存至服务器环境变量或密钥管理服务。停止服务使用 `docker compose down`，不带 `-v` 可保留数据卷。
## Production deployment (PostgreSQL)

The default Compose file keeps the demo's SQLite storage. For a multi-user or long-running deployment, create `.env` from `.env.example`, set a strong `SECRET_KEY` and `POSTGRES_PASSWORD`, then run:

```powershell
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --build
```

The application selects PostgreSQL automatically when `DATABASE_URL` is set. Configure your reverse proxy or cloud load balancer to terminate HTTPS before the container; do not expose a database port publicly.
