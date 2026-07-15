from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.core.fingerprint import request_fingerprint
from app.db.models import EmotionCheckin, Place
from app.db.session import get_db
from app.schemas.emotion import (
    EmotionCheckinRequest,
    EmotionCheckinResponse,
    EmotionRecommendationRequest,
    EmotionRecommendationResponse,
)
from app.services.emotion_recommendations import recommend_places
from app.services.place_emotion_profiles import apply_checkin_to_profile, serialize_emotion_profile
from app.services.vector_store import upsert_emotion_record


router = APIRouter(prefix="/emotions", tags=["emotions"])


@router.post("/recommendations", response_model=EmotionRecommendationResponse)
def emotion_recommendations(
    payload: EmotionRecommendationRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return recommend_places(session, settings, payload)


@router.post(
    "/checkins",
    response_model=EmotionCheckinResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_emotion_checkin(
    payload: EmotionCheckinRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    place = session.scalar(
        select(Place)
        .where(Place.id == payload.place_id)
        .options(selectinload(Place.emotion_profile))
    )
    if place is None:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다.")
    if place.emotion_profile is None:
        raise HTTPException(status_code=409, detail="장소 감정 프로필이 준비되지 않았습니다.")

    checkin = EmotionCheckin(
        place_id=place.id,
        fingerprint_hash=request_fingerprint(request, settings),
        before_emotion=payload.before_emotion,
        before_intensity=payload.before_intensity,
        after_emotion=payload.after_emotion,
        after_intensity=payload.after_intensity,
        travel_style=payload.travel_style,
    )
    session.add(checkin)
    apply_checkin_to_profile(
        place.emotion_profile,
        before_emotion=payload.before_emotion,
        after_emotion=payload.after_emotion,
        travel_style=payload.travel_style,
    )
    session.flush()

    try:
        vector_updated = await run_in_threadpool(
            upsert_emotion_record,
            settings,
            place,
            place.emotion_profile,
        )
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=503,
            detail="감정 체크인을 벡터 DB에 반영하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        ) from exc

    session.commit()
    return {
        "id": checkin.id,
        "place_id": place.id,
        "before_emotion": checkin.before_emotion,
        "before_intensity": checkin.before_intensity,
        "after_emotion": checkin.after_emotion,
        "after_intensity": checkin.after_intensity,
        "travel_style": checkin.travel_style,
        "created_at": checkin.created_at,
        "emotion": serialize_emotion_profile(place.emotion_profile),
        "vector_updated": vector_updated,
    }
