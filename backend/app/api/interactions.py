from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.fingerprint import request_fingerprint
from app.db.models import Place, PlaceLike, Review, ReviewLike
from app.db.session import get_db
from app.schemas.review import ToggleLikeResponse, ViewCountResponse

router = APIRouter(tags=["interactions"])


@router.post("/places/{place_id}/like", response_model=ToggleLikeResponse)
def toggle_place_like(
    place_id: int,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    place = session.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다.")
    fingerprint = request_fingerprint(request, settings)
    like = session.scalar(
        select(PlaceLike).where(
            PlaceLike.place_id == place_id, PlaceLike.fingerprint_hash == fingerprint
        )
    )
    if like:
        session.delete(like)
        place.like_count = max(0, place.like_count - 1)
        liked = False
    else:
        session.add(PlaceLike(place_id=place_id, fingerprint_hash=fingerprint))
        place.like_count += 1
        liked = True
    session.commit()
    return {"liked": liked, "like_count": place.like_count}


@router.post("/reviews/{review_id}/like", response_model=ToggleLikeResponse)
def toggle_review_like(
    review_id: int,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    review = session.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")
    fingerprint = request_fingerprint(request, settings)
    like = session.scalar(
        select(ReviewLike).where(
            ReviewLike.review_id == review_id, ReviewLike.fingerprint_hash == fingerprint
        )
    )
    if like:
        session.delete(like)
        review.like_count = max(0, review.like_count - 1)
        liked = False
    else:
        session.add(ReviewLike(review_id=review_id, fingerprint_hash=fingerprint))
        review.like_count += 1
        liked = True
    session.commit()
    return {"liked": liked, "like_count": review.like_count}


@router.post("/places/{place_id}/view", response_model=ViewCountResponse)
def increment_place_view(place_id: int, session: Session = Depends(get_db)) -> dict[str, int]:
    place = session.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다.")
    place.view_count += 1
    session.commit()
    return {"view_count": place.view_count}

