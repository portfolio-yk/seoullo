from __future__ import annotations

import json
import math
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import (
    ALLOWED_IMAGE_MEDIA_TYPES,
    DUPLICATE_RADIUS_METERS,
    MAX_IMAGE_BYTES,
    MAX_PLACE_IMAGES,
    MAX_TAG_LENGTH,
    MAX_TAGS_PER_PLACE,
)
from app.db.models import Place, PlaceImage, PlaceTag, Tag


def haversine_meters(latitude1: float, longitude1: float, latitude2: float, longitude2: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(latitude1)
    phi2 = math.radians(latitude2)
    delta_phi = math.radians(latitude2 - latitude1)
    delta_lambda = math.radians(longitude2 - longitude1)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def find_duplicate_places(
    session: Session,
    *,
    title: str,
    latitude: float,
    longitude: float,
    exclude_place_id: int | None = None,
) -> list[dict[str, object]]:
    # A 0.001 degree bounding box is roughly 111 m in latitude and keeps the
    # exact Haversine calculation limited to a small candidate set.
    normalized_title = " ".join(title.split()).casefold()
    statement = select(Place).where(
        func.lower(func.trim(Place.title)) == normalized_title,
        Place.latitude.between(latitude - 0.001, latitude + 0.001),
        Place.longitude.between(longitude - 0.0015, longitude + 0.0015),
    )
    if exclude_place_id is not None:
        statement = statement.where(Place.id != exclude_place_id)

    candidates: list[dict[str, object]] = []
    for place in session.scalars(statement):
        distance = haversine_meters(latitude, longitude, place.latitude, place.longitude)
        if distance <= DUPLICATE_RADIUS_METERS:
            candidates.append(
                {
                    "id": place.id,
                    "title": place.title,
                    "address": place.address,
                    "latitude": place.latitude,
                    "longitude": place.longitude,
                    "distance_meters": round(distance, 1),
                }
            )
    return sorted(candidates, key=lambda item: float(item["distance_meters"]))


def parse_tags(raw_tags: str) -> list[str]:
    value = raw_tags.strip()
    if not value:
        return []

    parsed: object
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = re.split(r"[,\s]+", value)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise HTTPException(status_code=422, detail="tags는 문자열 배열 또는 쉼표 구분 문자열이어야 합니다.")

    return normalize_tags(parsed)


def normalize_tags(items: list[str]) -> list[str]:
    unique: dict[str, str] = {}
    for item in items:
        display = " ".join(item.strip().lstrip("#").split())
        if not display:
            continue
        if len(display) > MAX_TAG_LENGTH:
            raise HTTPException(status_code=422, detail=f"태그는 {MAX_TAG_LENGTH}글자 이하여야 합니다.")
        unique.setdefault(display.casefold(), display)

    if len(unique) > MAX_TAGS_PER_PLACE:
        raise HTTPException(status_code=422, detail=f"태그는 최대 {MAX_TAGS_PER_PLACE}개까지 지정할 수 있습니다.")
    return list(unique.values())


def add_place_tags(session: Session, place: Place, tag_names: list[str]) -> bool:
    existing = {association.tag.normalized_name for association in place.place_tags}
    incoming = [name for name in tag_names if name.casefold() not in existing]
    if len(existing) + len(incoming) > MAX_TAGS_PER_PLACE:
        raise HTTPException(status_code=422, detail=f"장소별 태그는 최대 {MAX_TAGS_PER_PLACE}개까지 지정할 수 있습니다.")

    for name in incoming:
        normalized = name.casefold()
        tag = session.scalar(select(Tag).where(Tag.normalized_name == normalized))
        if tag is None:
            tag = Tag(name=name, normalized_name=normalized, usage_count=0)
            session.add(tag)
            session.flush()
        tag.usage_count += 1
        place.place_tags.append(PlaceTag(tag=tag))
    return bool(incoming)


def remove_place_tag(session: Session, place: Place, tag_name: str) -> bool:
    normalized = tag_name.strip().lstrip("#").casefold()
    association = next(
        (
            item
            for item in place.place_tags
            if item.tag.normalized_name == normalized
        ),
        None,
    )
    if association is None:
        return False
    association.tag.usage_count = max(0, association.tag.usage_count - 1)
    place.place_tags.remove(association)
    return True


def replace_place_tags(session: Session, place: Place, tag_names: list[str]) -> None:
    for association in list(place.place_tags):
        association.tag.usage_count = max(0, association.tag.usage_count - 1)
        place.place_tags.remove(association)
    session.flush()

    for name in tag_names:
        normalized = name.casefold()
        tag = session.scalar(select(Tag).where(Tag.normalized_name == normalized))
        if tag is None:
            tag = Tag(name=name, normalized_name=normalized, usage_count=0)
            session.add(tag)
            session.flush()
        tag.usage_count += 1
        place.place_tags.append(PlaceTag(tag=tag))


def _matches_signature(media_type: str, data: bytes) -> bool:
    if media_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if media_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if media_type == "image/webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


async def read_uploaded_images(files: list[UploadFile] | None) -> list[dict[str, object]]:
    if not files:
        return []
    if len(files) > MAX_PLACE_IMAGES:
        raise HTTPException(status_code=422, detail=f"이미지는 최대 {MAX_PLACE_IMAGES}장까지 업로드할 수 있습니다.")

    images: list[dict[str, object]] = []
    for file in files:
        media_type = (file.content_type or "").lower()
        if media_type not in ALLOWED_IMAGE_MEDIA_TYPES:
            raise HTTPException(status_code=415, detail="JPEG, PNG, WebP 이미지만 업로드할 수 있습니다.")
        data = await file.read(MAX_IMAGE_BYTES + 1)
        await file.close()
        if not data:
            raise HTTPException(status_code=422, detail="빈 이미지 파일은 업로드할 수 없습니다.")
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="이미지 한 장의 크기는 5MB 이하여야 합니다.")
        if not _matches_signature(media_type, data):
            raise HTTPException(status_code=415, detail="이미지 파일 형식과 Content-Type이 일치하지 않습니다.")
        images.append(
            {
                "filename": Path(file.filename or "image").name[:255],
                "media_type": media_type,
                "size_bytes": len(data),
                "data": data,
            }
        )
    return images


def append_images(place: Place, images: list[dict[str, object]]) -> None:
    if len(place.images) + len(images) > MAX_PLACE_IMAGES:
        raise HTTPException(status_code=422, detail=f"장소당 이미지는 최대 {MAX_PLACE_IMAGES}장입니다.")
    next_order = max((image.sort_order for image in place.images), default=-1) + 1
    for offset, image in enumerate(images):
        place.images.append(
            PlaceImage(
                filename=str(image["filename"]),
                media_type=str(image["media_type"]),
                size_bytes=int(image["size_bytes"]),
                data=bytes(image["data"]),
                sort_order=next_order + offset,
            )
        )


def require_user_place_password(place: Place, password: str) -> None:
    if place.source != "user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="원본 데이터 장소는 수정하거나 삭제할 수 없습니다.")
    if place.password != password:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비밀번호가 일치하지 않습니다.")


def place_tags(place: Place) -> list[str]:
    return [association.tag.name for association in place.place_tags]


def image_url(place: Place) -> str | None:
    if place.images:
        return f"/api/places/{place.id}/images/{place.images[0].id}"
    return place.primary_image_url or place.thumbnail_url or None


def serialize_place_summary(
    place: Place, *, latitude: float | None = None, longitude: float | None = None
) -> dict[str, object]:
    distance = None
    if latitude is not None and longitude is not None:
        distance = round(haversine_meters(latitude, longitude, place.latitude, place.longitude), 1)
    return {
        "id": place.id,
        "content_id": place.content_id,
        "source": place.source,
        "content_type": place.content_type,
        "content_type_id": place.content_type_id,
        "title": place.title,
        "description": place.description,
        "address": place.address,
        "detail_address": place.detail_address,
        "longitude": place.longitude,
        "latitude": place.latitude,
        "image_url": image_url(place),
        "tags": place_tags(place),
        "view_count": place.view_count,
        "like_count": place.like_count,
        "review_count": place.review_count,
        "average_rating": round(place.rating_sum / place.review_count, 1) if place.review_count else 0.0,
        "distance_meters": distance,
        "created_at": place.created_at,
        "updated_at": place.updated_at,
    }


def serialize_place_detail(place: Place, *, liked_by_me: bool = False) -> dict[str, object]:
    result = serialize_place_summary(place)
    result.update(
        {
            "liked_by_me": liked_by_me,
            "address_source": place.address_source,
            "zipcode": place.zipcode,
            "telephone": place.telephone,
            "map_level": place.map_level,
            "area_code": place.area_code,
            "sigungu_code": place.sigungu_code,
            "category1": place.category1,
            "category2": place.category2,
            "category3": place.category3,
            "classification1": place.classification1,
            "classification2": place.classification2,
            "classification3": place.classification3,
            "primary_image_url": place.primary_image_url,
            "thumbnail_url": place.thumbnail_url,
            "copyright_code": place.copyright_code,
            "images": [
                {
                    "id": image.id,
                    "filename": image.filename,
                    "media_type": image.media_type,
                    "size_bytes": image.size_bytes,
                    "sort_order": image.sort_order,
                    "url": f"/api/places/{place.id}/images/{image.id}",
                }
                for image in place.images
            ],
        }
    )
    return result
