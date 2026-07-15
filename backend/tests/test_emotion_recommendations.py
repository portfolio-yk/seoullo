from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.db.models import Place, PlaceEmotionProfile
from app.schemas.emotion import EmotionRecommendationRequest
from app.services.emotion_recommendations import recommend_places


def test_sqlite_fallback_returns_five_ranked_places(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'recommendations.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        for index in range(1, 7):
            session.add(
                Place(
                    content_id=f"emotion-{index}",
                    source="dataset",
                    region="서울",
                    content_type="관광지",
                    content_type_id="12",
                    title=f"추천 장소 {index}",
                    address="서울",
                    longitude=126.9 + index / 100,
                    latitude=37.5 + index / 100,
                    emotion_profile=PlaceEmotionProfile(
                        mood_fatigue=6 - index,
                        after_recovery=6 - index,
                        style_light_walk=6 - index,
                        mood_calm=index,
                    ),
                )
            )
        session.commit()

        payload = EmotionRecommendationRequest(
            mood=["지침"],
            afterFeeling=["회복"],
            style=["가볍게 산책"],
        )
        result = recommend_places(
            session,
            Settings(_env_file=None, pinecone_api_key=""),
            payload,
        )

    assert result["algorithm"] == "sqlite_cosine_fallback"
    assert len(result["items"]) == 5
    assert [item["rank"] for item in result["items"]] == [1, 2, 3, 4, 5]
    assert result["items"][0]["place"]["title"] == "추천 장소 1"
    assert result["items"][0]["similarity"] >= result["items"][-1]["similarity"]
    assert all(item["reason"] for item in result["items"])
    assert {item["reason_source"] for item in result["items"]} == {"rule"}


def test_request_rejects_duplicate_keywords() -> None:
    with pytest.raises(ValidationError):
        EmotionRecommendationRequest(
            mood=["지침", "지침"],
            afterFeeling=["회복"],
            style=["가볍게 산책"],
        )


def test_request_rejects_multiple_travel_styles() -> None:
    with pytest.raises(ValidationError):
        EmotionRecommendationRequest(
            mood=["지침"],
            afterFeeling=["회복", "해방"],
            style=["가볍게 산책", "조용히 혼자"],
        )
