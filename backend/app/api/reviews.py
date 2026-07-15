from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.fingerprint import request_fingerprint
from app.db.models import Place, Review, ReviewLike
from app.db.session import get_db
from app.schemas.place import DeleteResponse, PasswordRequest
from app.schemas.review import ReviewCreateRequest, ReviewListResponse, ReviewResponse, ReviewUpdateRequest
from app.services.reviews import serialize_review

router = APIRouter(tags=["reviews"])


def _get_place(session: Session, place_id: int) -> Place:
    place = session.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다.")
    return place


def _get_review(session: Session, review_id: int) -> Review:
    review = session.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")
    return review


def _validate_text(content: str, password: str) -> tuple[str, str]:
    normalized_content = content.strip()
    if not normalized_content:
        raise HTTPException(status_code=422, detail="리뷰는 공백으로만 구성할 수 없습니다.")
    if not password.strip():
        raise HTTPException(status_code=422, detail="비밀번호는 공백으로만 구성할 수 없습니다.")
    return normalized_content, password


@router.get("/places/{place_id}/reviews", response_model=ReviewListResponse)
def list_reviews(
    place_id: int,
    request: Request,
    sort: Literal["latest", "likes", "rating"] = Query(default="latest"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _get_place(session, place_id)
    statement = select(Review).where(Review.place_id == place_id)
    if sort == "likes":
        statement = statement.order_by(Review.like_count.desc(), Review.id.desc())
    elif sort == "rating":
        statement = statement.order_by(Review.rating.desc(), Review.id.desc())
    else:
        statement = statement.order_by(Review.created_at.desc(), Review.id.desc())

    total = session.scalar(select(func.count(Review.id)).where(Review.place_id == place_id)) or 0
    reviews = list(session.scalars(statement.offset((page - 1) * size).limit(size)))
    fingerprint = request_fingerprint(request, settings)
    liked_ids = set(
        session.scalars(
            select(ReviewLike.review_id).where(
                ReviewLike.review_id.in_([review.id for review in reviews]),
                ReviewLike.fingerprint_hash == fingerprint,
            )
        )
    ) if reviews else set()
    return {
        "items": [serialize_review(review, liked_by_me=review.id in liked_ids) for review in reviews],
        "page": page,
        "size": size,
        "total": total,
        "total_pages": (total + size - 1) // size,
    }


@router.post("/places/{place_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    place_id: int,
    payload: ReviewCreateRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    place = _get_place(session, place_id)
    content, password = _validate_text(payload.content, payload.password)
    fingerprint = request_fingerprint(request, settings)
    existing = session.scalar(
        select(Review).where(Review.place_id == place_id, Review.fingerprint_hash == fingerprint)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 브라우저에서는 장소당 리뷰를 하나만 작성할 수 있습니다. 기존 리뷰를 수정해 주세요.",
        )
    review = Review(
        place_id=place_id,
        fingerprint_hash=fingerprint,
        password=password,
        rating=payload.rating,
        content=content,
    )
    session.add(review)
    place.review_count += 1
    place.rating_sum += payload.rating
    session.commit()
    session.refresh(review)
    return serialize_review(review)


@router.put("/reviews/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: int,
    payload: ReviewUpdateRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    review = _get_review(session, review_id)
    if review.password != payload.password:
        raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")
    content, _password = _validate_text(payload.content, payload.password)
    place = _get_place(session, review.place_id)
    place.rating_sum += payload.rating - review.rating
    review.rating = payload.rating
    review.content = content
    session.commit()
    fingerprint = request_fingerprint(request, settings)
    liked = session.scalar(
        select(ReviewLike.id).where(
            ReviewLike.review_id == review.id, ReviewLike.fingerprint_hash == fingerprint
        )
    ) is not None
    return serialize_review(review, liked_by_me=liked)


@router.delete("/reviews/{review_id}", response_model=DeleteResponse)
def delete_review(
    review_id: int,
    payload: PasswordRequest,
    session: Session = Depends(get_db),
) -> dict[str, object]:
    review = _get_review(session, review_id)
    if review.password != payload.password:
        raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")
    place = _get_place(session, review.place_id)
    place.review_count = max(0, place.review_count - 1)
    place.rating_sum = max(0, place.rating_sum - review.rating)
    session.delete(review)
    session.commit()
    return {"deleted": True, "id": review_id}

