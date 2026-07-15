from __future__ import annotations

from math import sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.emotions import (
    EMOTION_COLUMNS,
    EMOTION_FIELDS,
    EMOTION_GROUP_WEIGHTS,
    EMOTION_VECTOR_DIMENSION,
    emotion_vector,
    selection_values,
)
from app.db.models import Place, PlaceEmotionProfile, PlaceTag
from app.schemas.emotion import EmotionRecommendationRequest
from app.services.places import serialize_place_summary
from app.services.recommendation_reasons import generate_recommendation_reasons


def _cosine(left: list[float], right: list[float]) -> float:
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def _profile_values(profile: PlaceEmotionProfile) -> dict[str, int]:
    return {column: int(getattr(profile, column)) for column in EMOTION_COLUMNS}


def _pinecone_matches(settings: Settings, query_vector: list[float]) -> list[tuple[int, float]]:
    if not settings.pinecone_emotion_configured:
        raise RuntimeError("Pinecone 감정 인덱스가 설정되지 않았습니다.")
    from pinecone import Pinecone

    index = Pinecone(api_key=settings.pinecone_api_key).Index(settings.pinecone_emotion_index_name)
    response = index.query(
        namespace=settings.pinecone_emotion_namespace,
        vector=query_vector,
        top_k=5,
        include_metadata=True,
    )
    matches: list[tuple[int, float]] = []
    for match in response.matches:
        place_id = int(match.metadata.get("place_id", str(match.id).split(":")[-1]))
        matches.append((place_id, float(match.score)))
    if len(matches) < 5:
        raise RuntimeError("Pinecone 추천 결과가 5개 미만입니다.")
    return matches


def _sqlite_matches(session: Session, query_vector: list[float]) -> list[tuple[int, float]]:
    profiles = session.scalars(select(PlaceEmotionProfile)).all()
    scored = [
        (profile.place_id, _cosine(query_vector, emotion_vector(_profile_values(profile))))
        for profile in profiles
        if any(_profile_values(profile).values())
    ]
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored[:5]


def _matched_keywords(
    profile: PlaceEmotionProfile,
    selections: dict[str, list[str]],
) -> list[dict[str, object]]:
    matches = [
        {
            "group": field.group,
            "keyword": field.keyword,
            "value": int(getattr(profile, field.column)),
        }
        for field in EMOTION_FIELDS
        if field.keyword in selections[field.group]
    ]
    return sorted(matches, key=lambda item: (-int(item["value"]), str(item["group"])))[:4]


def recommend_places(
    session: Session,
    settings: Settings,
    request: EmotionRecommendationRequest,
) -> dict[str, object]:
    selections = request.selections()
    query_vector = emotion_vector(selection_values(selections))
    try:
        scored_ids = _pinecone_matches(settings, query_vector)
        algorithm = "pinecone_cosine"
    except Exception:
        scored_ids = _sqlite_matches(session, query_vector)
        algorithm = "sqlite_cosine_fallback"

    place_ids = [place_id for place_id, _ in scored_ids]
    places = {
        place.id: place
        for place in session.scalars(
            select(Place)
            .where(Place.id.in_(place_ids))
            .options(
                selectinload(Place.images),
                selectinload(Place.place_tags).selectinload(PlaceTag.tag),
                selectinload(Place.emotion_profile),
            )
        ).unique()
    }
    items: list[dict[str, object]] = []
    for place_id, score in scored_ids:
        place = places.get(place_id)
        if place is None or place.emotion_profile is None:
            continue
        items.append(
            {
                "rank": len(items) + 1,
                "similarity": round(max(0.0, min(1.0, score)), 6),
                "matched_keywords": _matched_keywords(place.emotion_profile, selections),
                "place": serialize_place_summary(
                    place,
                    latitude=request.latitude,
                    longitude=request.longitude,
                ),
            }
        )

    reasons = generate_recommendation_reasons(settings, selections, items)
    for item in items:
        place_id = int(item["place"]["id"])
        item["reason"], item["reason_source"] = reasons[place_id]

    return {
        "algorithm": algorithm,
        "vector_dimension": EMOTION_VECTOR_DIMENSION,
        "weights": dict(EMOTION_GROUP_WEIGHTS),
        "items": items,
    }
