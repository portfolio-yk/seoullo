from typing import Literal

from pydantic import BaseModel, Field


ChatIntent = Literal[
    "place_recommendation",
    "emotion_recommendation",
    "festival_information",
    "location_information",
    "community_search",
    "general_information",
    "unknown",
]


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class ChatRequest(BaseModel):
    message: str = Field(default="", max_length=500)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=10)


class ChatSource(BaseModel):
    id: int
    content_id: str
    title: str
    content_type: str
    address: str
    image_url: str | None
    source: Literal["dataset", "user"]
    source_type: Literal["public_data", "community_post"]


class ChatRecommendation(BaseModel):
    id: int
    content_id: str
    title: str
    category: str
    address: str
    reason: str
    emotion_categories: list[str] = Field(default_factory=list, max_length=3)


class ChatResponse(BaseModel):
    answer: str
    intent: ChatIntent
    retrieval_method: Literal[
        "pinecone_semantic",
        "pinecone_lexical",
        "pinecone_emotion",
        "pinecone_hybrid",
        "sqlite_emotion",
        "sqlite_keyword",
        "sqlite_popular",
        "none",
    ]
    answer_source: Literal["openai", "rule"]
    recommendations: list[ChatRecommendation] = Field(default_factory=list, max_length=3)
    sources: list[ChatSource]
    fallback: bool
