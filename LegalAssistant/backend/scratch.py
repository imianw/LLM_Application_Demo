import asyncio
from app.core.config import get_settings
from app.services.legal_assistant import LegalAssistantService
from app.models.schemas import ChatRequest

async def main():
    service = LegalAssistantService(get_settings())
    request = ChatRequest(question="hello", history=[])
    try:
        response = await service.answer_question(request)
        print(response)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
