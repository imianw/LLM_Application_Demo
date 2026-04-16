# Legal Assistant

面向中国劳动法场景的 RAG 问答项目，当前版本已重构为前后端分离架构：

- `frontend/`: React + TypeScript + Vite 聊天界面
- `backend/`: FastAPI 服务，负责 LlamaIndex RAG、Qdrant 检索、重排和 LLM 问答
- `scripts/`: 法条抓取脚本
- `data/`: 法条数据文件

## 当前技术栈

- 前端：React + TypeScript + Vite
- 后端：FastAPI
- RAG 框架：LlamaIndex
- 向量数据库：Qdrant Cloud
- Embedding：DashScope `text-embedding-v4`
- Rerank：DashScope `qwen3-rerank`
- LLM：DashScope `qwen-plus`

## RAG 链路

项目当前使用的是“原项目风格”的召回主链：

1. 读取 `data/all_legal_clauses.json`
2. 转换为 `LlamaIndex TextNode`
3. 首次运行时将节点向量写入云端 `Qdrant`
4. 使用 `retriever.retrieve(...)` 做初始召回
5. 使用 `qwen3-rerank` 做重排
6. 使用 `qwen-plus` 生成最终回答

说明：

- 首次问答会更慢，因为需要完成向量化并写入 `Qdrant`
- 后续问答直接复用 `Qdrant` 集合，速度会明显快很多
- 若 `rerank` 或 `LLM` 异常，后端仍有兜底逻辑，保证接口尽量可用

## 目录结构

```text
LegalAssistant/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── core/
│   │   ├── models/
│   │   └── services/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── styles/
│   │   ├── api.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── scripts/
│   └── get_legal_clauses.py
├── data/
│   └── all_legal_clauses.json
├── .env.example
└── README.md
```

## 环境变量

复制 `.env.example` 为 `.env`，至少配置以下项目：

```bash
DASHSCOPE_API_KEY=your_dashscope_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

QDRANT_URL=https://your-cluster.region.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION_NAME=legal_assistant_labor_law

LLM_MODEL=qwen-plus
EMBED_MODEL=text-embedding-v4
RERANK_MODEL=qwen3-rerank

LLM_ENDPOINT=/chat/completions
EMBEDDING_ENDPOINT=/embeddings
RERANK_ENDPOINT=/rerank
RERANK_URL=https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank

CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

说明：

- `Embedding` 和 `LLM` 走百炼 OpenAI 兼容接口
- `Rerank` 优先尝试兼容接口，不可用时回退到百炼官方文本排序地址
- `QDRANT_COLLECTION_NAME` 默认可自定义，当前建议使用独立集合名避免和其他项目混用

## 启动方式

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. 安装并启动前端

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

启动后访问：

- 前端：[http://127.0.0.1:5173/](http://127.0.0.1:5173/)
- 后端：[http://127.0.0.1:8000](http://127.0.0.1:8000)

## 数据准备

如果 `data/all_legal_clauses.json` 不存在，可以重新抓取：

```bash
python scripts/get_legal_clauses.py
```

输出文件默认保存为 `data/all_legal_clauses.json`。

## 当前已完成

- 前后端分离重构
- React + TypeScript + Vite 前端
- FastAPI API 服务
- 恢复原项目风格的 LlamaIndex 检索链路
- 向量数据库切换到 Qdrant Cloud
- 接入 DashScope 的 Embedding / Rerank / LLM
- 无关问题范围拦截
- 前端相关性展示优化

## 后续可继续优化

- 将法条进一步切片，提升召回粒度
- 增加检索/重排/生成的耗时日志
- 补充接口测试和检索评测集
- 增加回答缓存和常见问题快速通道
- 优化前端错误提示与状态反馈
