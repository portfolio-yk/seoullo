from app.db.models import Review


def serialize_review(review: Review, *, liked_by_me: bool = False) -> dict[str, object]:
    return {
        "id": review.id,
        "place_id": review.place_id,
        "rating": review.rating,
        "content": review.content,
        "like_count": review.like_count,
        "liked_by_me": liked_by_me,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }

