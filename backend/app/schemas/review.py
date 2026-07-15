from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=3000)
    password: str = Field(min_length=1, max_length=200)


class ReviewUpdateRequest(ReviewCreateRequest):
    pass


class ReviewResponse(BaseModel):
    id: int
    place_id: int
    rating: int
    content: str
    like_count: int
    liked_by_me: bool
    created_at: datetime
    updated_at: datetime


class ReviewListResponse(BaseModel):
    items: list[ReviewResponse]
    page: int
    size: int
    total: int
    total_pages: int


class ToggleLikeResponse(BaseModel):
    liked: bool
    like_count: int


class ViewCountResponse(BaseModel):
    view_count: int


class PopularTagResponse(BaseModel):
    name: str
    usage_count: int

