from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Tag
from app.db.session import get_db
from app.schemas.review import PopularTagResponse

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/popular", response_model=list[PopularTagResponse])
def popular_tags(
    limit: int = Query(default=10, ge=1, le=10), session: Session = Depends(get_db)
) -> list[dict[str, object]]:
    tags = session.scalars(
        select(Tag).where(Tag.usage_count > 0).order_by(Tag.usage_count.desc(), Tag.name.asc()).limit(limit)
    )
    return [{"name": tag.name, "usage_count": tag.usage_count} for tag in tags]

