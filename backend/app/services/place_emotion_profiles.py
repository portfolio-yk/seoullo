from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.emotions import EMOTION_COLUMNS, EMOTION_COLUMN_BY_KEYWORD, emotion_payload
from app.db.models import EmotionCheckin, Place, PlaceEmotionProfile


class GeneratedPlaceEmotionProfile(BaseModel):
    mood_fatigue: int = Field(ge=1, le=5)
    mood_anxiety: int = Field(ge=1, le=5)
    mood_stifled: int = Field(ge=1, le=5)
    mood_excitement: int = Field(ge=1, le=5)
    mood_loneliness: int = Field(ge=1, le=5)
    mood_calm: int = Field(ge=1, le=5)
    after_recovery: int = Field(ge=1, le=5)
    after_release: int = Field(ge=1, le=5)
    after_vitality: int = Field(ge=1, le=5)
    after_comfort: int = Field(ge=1, le=5)
    after_immersion: int = Field(ge=1, le=5)
    after_excitement: int = Field(ge=1, le=5)
    style_quiet_solo: int = Field(ge=1, le=5)
    style_light_walk: int = Field(ge=1, le=5)
    style_new_stimulation: int = Field(ge=1, le=5)
    style_together: int = Field(ge=1, le=5)


class PlaceEmotionGenerationError(RuntimeError):
    pass


def place_emotion_context(place: Place) -> dict[str, object]:
    return {
        "title": place.title,
        "category": place.content_type,
        "description": place.description,
        "address": " ".join(filter(None, (place.address, place.detail_address))),
        "coordinates": {"latitude": place.latitude, "longitude": place.longitude},
        "tags": [association.tag.name for association in place.place_tags],
    }


def generate_place_emotion_values(
    settings: Settings,
    context: dict[str, object],
    *,
    client: Any | None = None,
) -> dict[str, int]:
    if client is None and not settings.openai_api_key:
        raise PlaceEmotionGenerationError("OPENAI_API_KEY가 설정되지 않았습니다.")
    try:
        if client is None:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_reason_timeout_seconds,
            )
        response = client.responses.parse(
            model=settings.openai_chat_model,
            reasoning={"effort": "minimal"},
            max_output_tokens=2000,
            store=False,
            input=[
                {
                    "role": "system",
                    "content": (
                        "당신은 서울 여행 장소의 감정 특성을 분류합니다. 입력된 장소 정보만 근거로 "
                        "16개 감정 항목을 각각 1~5 정수로 평가하세요. 1은 관련성이 매우 낮음, "
                        "5는 매우 높음을 뜻합니다. 정보가 부족한 항목은 3을 사용하세요. "
                        "장소의 현재 분위기와 방문 후 기대 감정, 적합한 여행 방식을 서로 구분해 "
                        "평가하고 입력에 없는 시설이나 사실은 추측하지 마세요."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False, separators=(",", ":")),
                },
            ],
            text_format=GeneratedPlaceEmotionProfile,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("OpenAI structured response was empty")
        values = parsed.model_dump()
        if set(values) != set(EMOTION_COLUMNS):
            raise ValueError("OpenAI emotion fields did not match the fixed schema")
        return {column: int(values[column]) for column in EMOTION_COLUMNS}
    except PlaceEmotionGenerationError:
        raise
    except Exception as exc:
        raise PlaceEmotionGenerationError(
            "장소 감정 프로필을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."
        ) from exc


def _checkin_increments(session: Session, place_id: int) -> dict[str, int]:
    increments = {column: 0 for column in EMOTION_COLUMNS}
    checkins = session.scalars(
        select(EmotionCheckin).where(EmotionCheckin.place_id == place_id)
    ).all()
    for checkin in checkins:
        increments[EMOTION_COLUMN_BY_KEYWORD[("mood", checkin.before_emotion)]] += 1
        increments[EMOTION_COLUMN_BY_KEYWORD[("afterFeeling", checkin.after_emotion)]] += 1
        increments[EMOTION_COLUMN_BY_KEYWORD[("style", checkin.travel_style)]] += 1
    return increments


def replace_generated_profile(
    session: Session,
    place: Place,
    base_values: dict[str, int],
) -> PlaceEmotionProfile:
    profile = place.emotion_profile
    if profile is None:
        profile = PlaceEmotionProfile(place=place)
        session.add(profile)
    increments = _checkin_increments(session, place.id) if place.id is not None else {
        column: 0 for column in EMOTION_COLUMNS
    }
    for column in EMOTION_COLUMNS:
        setattr(profile, column, int(base_values[column]) + increments[column])
    return profile


def apply_checkin_to_profile(
    profile: PlaceEmotionProfile,
    *,
    before_emotion: str,
    after_emotion: str,
    travel_style: str,
) -> None:
    for group, keyword in (
        ("mood", before_emotion),
        ("afterFeeling", after_emotion),
        ("style", travel_style),
    ):
        column = EMOTION_COLUMN_BY_KEYWORD[(group, keyword)]
        setattr(profile, column, int(getattr(profile, column)) + 1)


def serialize_emotion_profile(profile: PlaceEmotionProfile) -> dict[str, dict[str, int]]:
    return emotion_payload({column: int(getattr(profile, column)) for column in EMOTION_COLUMNS})
