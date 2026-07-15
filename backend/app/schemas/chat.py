from typing import Literal

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=10)


class ChatSource(BaseModel):
    id: int
    title: str
    content_type: str
    address: str
    image_url: str | None
    source: Literal["dataset", "user"]


class ChatResponse(BaseModel):
    answer: str
    retrieval_method: Literal["pinecone_semantic", "sqlite_keyword", "sqlite_popular"]
    answer_source: Literal["openai", "rule"]
    sources: list[ChatSource]
