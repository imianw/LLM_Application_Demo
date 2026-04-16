import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import httpx
from llama_index.core import Settings as LlamaSettings
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from app.core.config import Settings, get_settings
from app.models.schemas import ChatRequest, ChatResponse, Citation
from app.services.modelscope_client import DashScopeClient


SYSTEM_PROMPT = """你是一个严谨的中国劳动法助手。
请仅根据提供的法律条文回答问题。
如果依据不足，要明确告知用户需要进一步核实，并建议咨询专业律师。
回答时优先给出结论，再引用相关法条要点，禁止编造法律依据。"""

LABOR_LAW_KEYWORDS = (
    "劳动",
    "用人单位",
    "员工",
    "公司",
    "入职",
    "离职",
    "辞退",
    "辞职",
    "开除",
    "劳动合同",
    "合同",
    "试用期",
    "工资",
    "薪资",
    "社保",
    "五险一金",
    "加班",
    "工时",
    "补偿",
    "赔偿",
    "经济补偿",
    "仲裁",
    "工伤",
    "年假",
    "休假",
    "产假",
    "孕期",
    "考勤",
    "调岗",
    "裁员",
    "劳务派遣",
)


def load_and_validate_json_files(data_file: Path) -> list[dict[str, Any]]:
    if not data_file.exists():
        raise FileNotFoundError(f"未找到法律数据文件: {data_file}")

    all_data: list[dict[str, Any]] = []
    with open(data_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"文件 {data_file.name} 根元素应为列表")

    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"文件 {data_file.name} 包含非字典元素")

        for key, value in item.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError(f"文件 {data_file.name} 存在非字符串法条数据")

        all_data.append({"content": item, "metadata": {"source": data_file.name}})

    return all_data


def create_nodes(raw_data: list[dict[str, Any]]) -> list[TextNode]:
    nodes: list[TextNode] = []
    for entry in raw_data:
        law_dict = entry["content"]
        source_file = entry["metadata"]["source"]

        for full_title, content in law_dict.items():
            parts = full_title.split(" ", 1)
            law_name = parts[0] if parts else "未知法律"
            article = parts[1] if len(parts) > 1 else "未知条款"

            nodes.append(
                TextNode(
                    text=content,
                    id_=str(uuid5(NAMESPACE_URL, f"{source_file}::{full_title}")),
                    metadata={
                        "source_id": f"{source_file}::{full_title}",
                        "law_name": law_name,
                        "article": article,
                        "full_title": full_title,
                        "source_file": source_file,
                        "content_type": "legal_article",
                    },
                )
            )

    return nodes


class LegalAssistantService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = DashScopeClient(settings)
        self._retriever = None

    def _build_embed_model(self) -> OpenAILikeEmbedding:
        if not self.settings.dashscope_api_key:
            raise ValueError("尚未配置 DASHSCOPE_API_KEY。")

        return OpenAILikeEmbedding(
            model_name=self.settings.embed_model,
            api_key=self.settings.dashscope_api_key,
            api_base=self.settings.dashscope_base_url,
            timeout=self.settings.request_timeout_seconds,
        )

    def _build_qdrant_client(self) -> QdrantClient:
        if not self.settings.qdrant_url or not self.settings.qdrant_api_key:
            raise ValueError("尚未配置 Qdrant 云端连接。请提供 QDRANT_URL 和 QDRANT_API_KEY。")

        return QdrantClient(
            url=self.settings.qdrant_url,
            api_key=self.settings.qdrant_api_key,
            timeout=self.settings.request_timeout_seconds,
        )

    def _collection_has_points(self, client: QdrantClient) -> bool:
        try:
            count_result = client.count(
                collection_name=self.settings.qdrant_collection_name,
                exact=True,
            )
        except Exception:
            return False

        return int(getattr(count_result, "count", 0)) > 0

    def _ensure_rag_pipeline(self):
        if self._retriever is not None:
            return self._retriever

        embed_model = self._build_embed_model()
        qdrant_client = self._build_qdrant_client()
        vector_store = QdrantVectorStore(
            client=qdrant_client,
            collection_name=self.settings.qdrant_collection_name,
            batch_size=self.settings.qdrant_batch_size,
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        LlamaSettings.embed_model = embed_model

        if self._collection_has_points(qdrant_client):
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=embed_model,
            )
        else:
            raw_data = load_and_validate_json_files(self.settings.data_file)
            nodes = create_nodes(raw_data)
            storage_context.docstore.add_documents(nodes)
            index = VectorStoreIndex(
                nodes,
                storage_context=storage_context,
                embed_model=embed_model,
                show_progress=True,
            )

        self._retriever = index.as_retriever(
            similarity_top_k=self.settings.retrieval_top_k,
            vector_store_query_mode="default",
        )
        return self._retriever

    def _is_question_in_scope(self, question: str, top_score: float | None) -> bool:
        normalized_question = question.strip().lower()
        has_domain_keyword = any(keyword in normalized_question for keyword in LABOR_LAW_KEYWORDS)

        if has_domain_keyword:
            return True

        if top_score is None:
            return False

        return top_score >= 0.55

    def _build_out_of_scope_answer(self) -> str:
        return (
            "我目前只提供中国劳动法和劳动合同相关咨询。"
            "如果你的问题与入职、离职、工资、社保、加班、工伤、解除劳动合同等有关，欢迎继续提问；"
            "如果是其他领域的问题，我暂时无法准确回答。"
        )

    async def _rerank(self, question: str, candidates: list[Any]) -> list[Citation]:
        if not candidates:
            return []

        try:
            rerank_results = await self.client.rerank(
                question,
                [node.node.get_content() for node in candidates],
            )

            citations: list[Citation] = []
            for result in rerank_results:
                index = result.get("index")
                score = float(result.get("relevance_score", 0.0))
                if index is None or index >= len(candidates) or score < self.settings.min_rerank_score:
                    continue

                source_node = candidates[index].node
                citations.append(
                    Citation(
                        title=source_node.metadata.get("full_title", "未知条文"),
                        law_name=source_node.metadata.get("law_name", "未知法律"),
                        source_file=source_node.metadata.get("source_file", "未知来源"),
                        content=source_node.get_content(),
                        score=score,
                    )
                )

            if citations:
                return citations[: self.settings.rerank_top_k]
        except (httpx.HTTPError, ValueError):
            pass

        return [
            Citation(
                title=node.node.metadata.get("full_title", "未知条文"),
                law_name=node.node.metadata.get("law_name", "未知法律"),
                source_file=node.node.metadata.get("source_file", "未知来源"),
                content=node.node.get_content(),
                score=float(node.score or 0.0),
            )
            for node in candidates[: self.settings.rerank_top_k]
        ]

    async def answer_question(self, request: ChatRequest) -> ChatResponse:
        retriever = self._ensure_rag_pipeline()
        candidates = retriever.retrieve(request.question)
        top_score = float(candidates[0].score or 0.0) if candidates else None

        if not self._is_question_in_scope(request.question, top_score):
            return ChatResponse(answer=self._build_out_of_scope_answer(), citations=[])

        citations = await self._rerank(request.question, candidates)

        if not citations:
            return ChatResponse(
                answer="未检索到足够相关的法律条文。请尝试补充事实背景，或咨询专业律师进一步确认。",
                citations=[],
            )

        context = "\n".join(
            f"{index}. [{citation.title}] {citation.content}"
            for index, citation in enumerate(citations, start=1)
        )

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(message.model_dump() for message in request.history[-6:])
        messages.append(
            {
                "role": "user",
                "content": (
                    f"用户问题：{request.question}\n\n"
                    f"可用法律依据：\n{context}\n\n"
                    "请基于以上依据作答，并在结尾提醒本回答仅供参考。"
                ),
            }
        )

        try:
            answer = await self.client.chat(messages)
        except (httpx.HTTPError, ValueError):
            answer = self._build_fallback_answer(citations)

        return ChatResponse(answer=answer, citations=citations)

    def _build_fallback_answer(self, citations: list[Citation]) -> str:
        if not citations:
            return "未检索到足够相关的法律条文。请尝试补充事实背景，或咨询专业律师进一步确认。"

        lead = "根据检索到的相关法条，与你问题最相关的依据如下："
        details = "\n".join(
            f"{index}. {citation.title}：{citation.content}"
            for index, citation in enumerate(citations, start=1)
        )
        closing = "以上内容仅供参考，若涉及具体争议处理，请结合事实材料并咨询专业律师。"
        return f"{lead}\n{details}\n{closing}"


@lru_cache
def get_legal_assistant_service() -> LegalAssistantService:
    return LegalAssistantService(get_settings())
