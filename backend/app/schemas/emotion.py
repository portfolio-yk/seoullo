from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.core.emotions import EMOTION_FIELDS
from app.schemas.place import PlaceSummaryResponse


MoodKeyword = Literal["지침", "불안", "답답함", "설렘", "외로움", "평온함"]
AfterKeyword = Literal["회복", "해방", "활력", "위로", "몰입", "설렘"]
StyleKeyword = Literal["조용히 혼자", "가볍게 산책", "새로운 자극", "누군가와 함께"]


class EmotionRecommendationRequest(BaseModel):
    mood: Annotated[list[MoodKeyword], Field(min_length=1, max_length=6)]
    afterFeeling: Annotated[list[AfterKeyword], Field(min_length=1, max_length=6)]
    style: Annotated[list[StyleKeyword], Field(min_length=1, max_length=1)]
    latitude: float | None = Field(default=None, ge=33.0, le=39.5)
    longitude: float | None = Field(default=None, ge=124.0, le=132.0)

    @model_validator(mode="after")
    def validate_unique_and_coordinates(self):
        for name in ("mood", "afterFeeling", "style"):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"{name} 키워드는 중복될 수 없습니다.")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("거리 계산에는 위도와 경도가 모두 필요합니다.")
        return self

    def selections(self) -> dict[str, list[str]]:
        return {
            "mood": list(self.mood),
            "afterFeeling": list(self.afterFeeling),
            "style": list(self.style),
        }


class EmotionMatchResponse(BaseModel):
    group: str
    keyword: str
    value: int


class EmotionRecommendationItem(BaseModel):
    rank: int
    similarity: float
    matched_keywords: list[EmotionMatchResponse]
    reason: str
    reason_source: Literal["openai", "rule"]
    place: PlaceSummaryResponse


class EmotionRecommendationResponse(BaseModel):
    algorithm: Literal["pinecone_cosine", "sqlite_cosine_fallback"]
    vector_dimension: int
    weights: dict[str, float]
    items: list[EmotionRecommendationItem]


class EmotionCheckinRequest(BaseModel):
    place_id: int = Field(ge=1)
    before_emotion: MoodKeyword
    before_intensity: int = Field(ge=1, le=5)
    after_emotion: AfterKeyword
    after_intensity: int = Field(ge=1, le=5)
    travel_style: StyleKeyword


class EmotionCheckinResponse(BaseModel):
    id: int
    place_id: int
    before_emotion: str
    before_intensity: int
    after_emotion: str
    after_intensity: int
    travel_style: str
    created_at: datetime
    emotion: dict[str, dict[str, int]]
    vector_updated: bool


EMOTION_OPTIONS = {
    group: [field.keyword for field in EMOTION_FIELDS if field.group == group]
    for group in ("mood", "afterFeeling", "style")
}
