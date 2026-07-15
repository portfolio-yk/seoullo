from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.emotions import router as emotions_router
from app.core.config import Settings, get_settings
from app.core.emotions import EMOTION_COLUMNS
from app.db.base import Base
from app.db.models import EmotionCheckin, Place, PlaceEmotionProfile
from app.db.session import get_db
from app.services.place_emotion_profiles import (
    GeneratedPlaceEmotionProfile,
    generate_place_emotion_values,
    replace_generated_profile,
)


def _profile_values(value: int = 2) -> dict[str, int]:
    return {column: value for column in EMOTION_COLUMNS}


def test_ai_place_profile_uses_one_structured_response() -> None:
    parsed = GeneratedPlaceEmotionProfile(**_profile_values(3))
    calls: list[dict[str, object]] = []

    class FakeResponses:
        def parse(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_parsed=parsed)

    values = generate_place_emotion_values(
        Settings(_env_file=None, openai_api_key="test-key"),
        {"title": "테스트 공원", "category": "관광지", "description": "조용한 산책 공간"},
        client=SimpleNamespace(responses=FakeResponses()),
    )

    assert len(calls) == 1
    assert calls[0]["text_format"] is GeneratedPlaceEmotionProfile
    assert calls[0]["store"] is False
    assert values == _profile_values(3)


def test_regenerated_profile_preserves_existing_checkin_increments(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'profile.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        place = Place(
            content_id=None,
            source="user",
            region="서울",
            content_type="관광지",
            content_type_id="12",
            title="사용자 장소",
            description="설명",
            longitude=126.98,
            latitude=37.56,
            password="password",
            emotion_profile=PlaceEmotionProfile(**_profile_values(2)),
        )
        session.add(place)
        session.flush()
        session.add(
            EmotionCheckin(
                place_id=place.id,
                fingerprint_hash="fingerprint",
                before_emotion="지침",
                before_intensity=4,
                after_emotion="회복",
                after_intensity=5,
                travel_style="가볍게 산책",
            )
        )
        session.commit()

        replace_generated_profile(session, place, _profile_values(3))

        assert place.emotion_profile.mood_fatigue == 4
        assert place.emotion_profile.after_recovery == 4
        assert place.emotion_profile.style_light_walk == 4
        assert place.emotion_profile.mood_anxiety == 3


@pytest.fixture
def checkin_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'checkins.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with testing_session() as session:
        session.add(
            Place(
                content_id="dataset-checkin",
                source="dataset",
                region="서울",
                content_type="관광지",
                content_type_id="12",
                title="체크인 장소",
                longitude=126.98,
                latitude=37.56,
                emotion_profile=PlaceEmotionProfile(**_profile_values(2)),
            )
        )
        session.commit()

    captured: list[dict[str, int]] = []

    def fake_upsert(_settings, _place, profile):
        captured.append({column: int(getattr(profile, column)) for column in EMOTION_COLUMNS})
        return True

    monkeypatch.setattr("app.api.emotions.upsert_emotion_record", fake_upsert)

    def override_db():
        with testing_session() as session:
            yield session

    app = FastAPI()
    app.include_router(emotions_router, prefix="/api")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        fingerprint_secret="test-secret",
        pinecone_api_key="test-pinecone",
    )
    with TestClient(app) as client:
        yield client, testing_session, captured


def test_checkin_increments_three_selected_columns_and_syncs_vector(checkin_client) -> None:
    client, testing_session, captured = checkin_client
    response = client.post(
        "/api/emotions/checkins",
        headers={"x-forwarded-for": "203.0.113.30", "user-agent": "Checkin-Test"},
        json={
            "place_id": 1,
            "before_emotion": "지침",
            "before_intensity": 4,
            "after_emotion": "회복",
            "after_intensity": 5,
            "travel_style": "가볍게 산책",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["vector_updated"] is True
    assert payload["emotion"]["mood"]["지침"] == 3
    assert payload["emotion"]["afterFeeling"]["회복"] == 3
    assert payload["emotion"]["style"]["가볍게 산책"] == 3
    assert payload["emotion"]["mood"]["불안"] == 2
    assert "satisfaction" not in payload
    assert captured[0]["mood_fatigue"] == 3

    with testing_session() as session:
        assert session.scalar(select(func.count(EmotionCheckin.id))) == 1
        profile = session.get(PlaceEmotionProfile, 1)
        assert profile.mood_fatigue == 3
        assert profile.after_recovery == 3
        assert profile.style_light_walk == 3


def test_checkin_rolls_back_when_vector_sync_fails(checkin_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, testing_session, _captured = checkin_client
    monkeypatch.setattr(
        "app.api.emotions.upsert_emotion_record",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("pinecone unavailable")),
    )

    response = client.post(
        "/api/emotions/checkins",
        json={
            "place_id": 1,
            "before_emotion": "불안",
            "before_intensity": 3,
            "after_emotion": "위로",
            "after_intensity": 4,
            "travel_style": "조용히 혼자",
        },
    )

    assert response.status_code == 503
    with testing_session() as session:
        assert session.scalar(select(func.count(EmotionCheckin.id))) == 0
        assert session.get(PlaceEmotionProfile, 1).mood_anxiety == 2
