from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import ChatRequest, ChatResponse
from app.services.legal_assistant import LegalAssistantService, get_legal_assistant_service


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: LegalAssistantService = Depends(get_legal_assistant_service),
) -> ChatResponse:
    try:
        return await service.answer_question(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
