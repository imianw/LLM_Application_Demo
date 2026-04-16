from typing import Any

import httpx

from app.core.config import Settings


class DashScopeClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._headers = {
            "Authorization": f"Bearer {settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }

    def _ensure_api_key(self) -> None:
        if not self.settings.dashscope_api_key:
            raise ValueError(
                "尚未配置 DASHSCOPE_API_KEY。请先提供你的百炼 API Key，我再帮你完成联调。"
            )

    async def _post_compatible(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_api_key()
        async with httpx.AsyncClient(
            base_url=self.settings.dashscope_base_url,
            timeout=self.settings.request_timeout_seconds,
        ) as client:
            response = await client.post(endpoint, headers=self._headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def _post_full_url(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_api_key()
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(url, headers=self._headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        batch_size = max(1, self.settings.embedding_batch_size)

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            payload = {
                "model": self.settings.embed_model,
                "input": batch,
                "encoding_format": "float",
            }
            data = await self._post_compatible(self.settings.embedding_endpoint, payload)
            embeddings = data.get("data", [])
            all_embeddings.extend(item["embedding"] for item in embeddings)

        return all_embeddings

    async def rerank(self, query: str, documents: list[str]) -> list[dict[str, Any]]:
        compatible_payload = {
            "model": self.settings.rerank_model,
            "query": query,
            "documents": documents,
            "top_n": self.settings.rerank_top_k,
        }

        try:
            data = await self._post_compatible(self.settings.rerank_endpoint, compatible_payload)
            return data.get("results", data.get("data", []))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise

        official_payload = {
            "model": self.settings.rerank_model,
            "input": {
                "query": query,
                "documents": documents,
            },
            "parameters": {
                "top_n": self.settings.rerank_top_k,
                "return_documents": False,
            },
        }
        data = await self._post_full_url(self.settings.rerank_url, official_payload)
        return data.get("output", {}).get("results", [])

    async def chat(self, messages: list[dict[str, str]]) -> str:
        payload = {"model": self.settings.llm_model, "messages": messages, "temperature": 0.2}
        data = await self._post_compatible(self.settings.llm_endpoint, payload)
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("百炼 LLM 未返回有效结果。")
        return choices[0]["message"]["content"].strip()
