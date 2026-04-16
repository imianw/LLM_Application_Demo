from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)


class Citation(BaseModel):
    title: str
    law_name: str
    source_file: str
    content: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
