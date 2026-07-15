from datetime import datetime

from pydantic import BaseModel, Field


class PlaceImageResponse(BaseModel):
    id: int
    filename: str
    media_type: str
    size_bytes: int
    sort_order: int
    url: str


class PlaceSummaryResponse(BaseModel):
    id: int
    content_id: str | None
    source: str
    content_type: str
    content_type_id: str
    title: str
    description: str
    address: str
    detail_address: str
    longitude: float
    latitude: float
    image_url: str | None
    tags: list[str]
    view_count: int
    like_count: int
    review_count: int
    average_rating: float
    distance_meters: float | None = None
    created_at: datetime
    updated_at: datetime


class PlaceDetailResponse(PlaceSummaryResponse):
    liked_by_me: bool = False
    address_source: str
    zipcode: str
    telephone: str
    map_level: str
    area_code: str
    sigungu_code: str
    category1: str
    category2: str
    category3: str
    classification1: str
    classification2: str
    classification3: str
    primary_image_url: str
    thumbnail_url: str
    copyright_code: str
    images: list[PlaceImageResponse]


class PlaceListResponse(BaseModel):
    items: list[PlaceSummaryResponse]
    page: int
    size: int
    total: int
    total_pages: int


class CategoryCountResponse(BaseModel):
    content_type_id: str
    content_type: str
    count: int


class PlaceMapPointResponse(BaseModel):
    id: int
    source: str
    content_type: str
    content_type_id: str
    title: str
    address: str
    longitude: float
    latitude: float
    image_url: str | None
    view_count: int
    like_count: int
    review_count: int
    average_rating: float
    distance_meters: float | None = None


class DuplicateCandidateResponse(BaseModel):
    id: int
    title: str
    address: str
    latitude: float
    longitude: float
    distance_meters: float


class DuplicateCheckResponse(BaseModel):
    has_duplicates: bool
    radius_meters: float
    candidates: list[DuplicateCandidateResponse]


class PasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class DeleteResponse(BaseModel):
    deleted: bool
    id: int
