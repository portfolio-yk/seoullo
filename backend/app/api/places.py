from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.core.constants import DUPLICATE_RADIUS_METERS, SUPPORTED_CONTENT_TYPES
from app.core.fingerprint import request_fingerprint
from app.db.models import Place, PlaceImage, PlaceLike, PlaceTag, Tag
from app.db.session import get_db
from app.schemas.place import (
    CategoryCountResponse,
    DeleteResponse,
    DuplicateCheckResponse,
    PasswordRequest,
    PlaceDetailResponse,
    PlaceListResponse,
    PlaceMapPointResponse,
)
from app.services.places import (
    append_images,
    find_duplicate_places,
    haversine_meters,
    image_url,
    parse_tags,
    read_uploaded_images,
    replace_place_tags,
    require_user_place_password,
    serialize_place_detail,
    serialize_place_summary,
)
from app.services.kakao_local import KakaoLocalError, reverse_geocode
from app.services.place_emotion_profiles import (
    PlaceEmotionGenerationError,
    generate_place_emotion_values,
    place_emotion_context,
    replace_generated_profile,
)
from app.services.vector_store import delete_place_vectors, sync_place_vectors

router = APIRouter(prefix="/places", tags=["places"])


def _place_statement():
    return select(Place).options(
        selectinload(Place.images),
        selectinload(Place.place_tags).selectinload(PlaceTag.tag),
        selectinload(Place.emotion_profile),
    )


def _get_place(session: Session, place_id: int) -> Place:
    place = session.scalar(_place_statement().where(Place.id == place_id))
    if place is None:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다.")
    return place


def _validate_coordinates(latitude: float, longitude: float) -> None:
    if not 33.0 <= latitude <= 39.5 or not 124.0 <= longitude <= 132.0:
        raise HTTPException(status_code=422, detail="대한민국 범위의 유효한 위도와 경도를 입력해 주세요.")


def _duplicate_warning(candidates: list[dict[str, object]]) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "DUPLICATE_PLACE_WARNING",
            "message": "같은 이름의 장소가 50m 이내에 있습니다. 확인 후 allow_duplicate=true로 다시 요청하세요.",
            "candidates": candidates,
        },
    )


async def _refresh_user_place_profile(
    session: Session,
    settings: Settings,
    place: Place,
) -> None:
    try:
        values = await run_in_threadpool(
            generate_place_emotion_values,
            settings,
            place_emotion_context(place),
        )
        profile = replace_generated_profile(session, place, values)
        session.flush()
        await run_in_threadpool(sync_place_vectors, settings, place, profile)
    except PlaceEmotionGenerationError as exc:
        session.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=503,
            detail="장소 감정 벡터를 동기화하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        ) from exc


@router.get("", response_model=PlaceListResponse)
def list_places(
    q: str = Query(default="", max_length=100),
    content_type_id: str | None = Query(default=None),
    source: Literal["dataset", "user"] | None = Query(default=None),
    ids: str | None = Query(default=None, max_length=1000),
    sort: Literal["latest", "rating", "likes", "distance"] = Query(default="latest"),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    radius_meters: int | None = Query(default=None, ge=100, le=50000),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="거리 계산에는 위도와 경도가 모두 필요합니다.")
    if latitude is not None and longitude is not None:
        _validate_coordinates(latitude, longitude)
    if radius_meters is not None and (latitude is None or longitude is None):
        raise HTTPException(status_code=422, detail="반경 검색에는 위도와 경도가 모두 필요합니다.")
    if sort == "distance" and (latitude is None or longitude is None):
        raise HTTPException(status_code=422, detail="거리순 정렬에는 위도와 경도가 필요합니다.")
    if content_type_id is not None and content_type_id not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="지원하지 않는 장소 카테고리입니다.")

    statement = _place_statement()
    count_statement = select(func.count(func.distinct(Place.id))).select_from(Place)
    filters = []
    keyword = q.strip()

    if content_type_id:
        filters.append(Place.content_type_id == content_type_id)
    if source:
        filters.append(Place.source == source)
    if radius_meters is not None and latitude is not None and longitude is not None:
        latitude_meters = (Place.latitude - latitude) * 111_320.0
        longitude_meters = (Place.longitude - longitude) * 88_000.0
        filters.append(
            latitude_meters * latitude_meters + longitude_meters * longitude_meters
            <= radius_meters * radius_meters
        )
    if ids:
        try:
            place_ids = list(dict.fromkeys(int(value) for value in ids.split(",") if value.strip()))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="ids는 쉼표로 구분한 숫자여야 합니다.") from exc
        if len(place_ids) > 100:
            raise HTTPException(status_code=422, detail="한 번에 최대 100개의 장소를 조회할 수 있습니다.")
        filters.append(Place.id.in_(place_ids) if place_ids else Place.id == -1)

    if keyword.startswith("#"):
        normalized_tag = keyword.lstrip("#").strip().casefold()
        statement = statement.join(Place.place_tags).join(PlaceTag.tag)
        count_statement = count_statement.join(Place.place_tags).join(PlaceTag.tag)
        filters.append(Tag.normalized_name == normalized_tag)
    elif keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                Place.title.ilike(pattern),
                Place.description.ilike(pattern),
                Place.address.ilike(pattern),
                Place.detail_address.ilike(pattern),
            )
        )

    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)

    average_rating = case(
        (Place.review_count > 0, Place.rating_sum * 1.0 / Place.review_count), else_=0.0
    )
    if sort == "likes":
        statement = statement.order_by(Place.like_count.desc(), Place.id.desc())
    elif sort == "rating":
        statement = statement.order_by(average_rating.desc(), Place.review_count.desc(), Place.id.desc())
    elif sort == "distance":
        latitude_delta = Place.latitude - float(latitude)
        longitude_delta = Place.longitude - float(longitude)
        statement = statement.order_by(
            (latitude_delta * latitude_delta + longitude_delta * longitude_delta).asc(), Place.id.asc()
        )
    else:
        statement = statement.order_by(Place.created_at.desc(), Place.id.desc())

    total = session.scalar(count_statement) or 0
    places = list(session.scalars(statement.offset((page - 1) * size).limit(size)).unique())
    return {
        "items": [
            serialize_place_summary(place, latitude=latitude, longitude=longitude) for place in places
        ],
        "page": page,
        "size": size,
        "total": total,
        "total_pages": (total + size - 1) // size,
    }


@router.get("/categories", response_model=list[CategoryCountResponse])
def list_categories(session: Session = Depends(get_db)) -> list[dict[str, object]]:
    counts = dict(
        session.execute(
            select(Place.content_type_id, func.count(Place.id)).group_by(Place.content_type_id)
        ).all()
    )
    return [
        {"content_type_id": code, "content_type": name, "count": int(counts.get(code, 0))}
        for code, name in SUPPORTED_CONTENT_TYPES.items()
    ]


@router.get("/map-points", response_model=list[PlaceMapPointResponse])
def list_map_points(
    content_type_id: str | None = Query(default=None),
    ids: str | None = Query(default=None, max_length=1000),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    radius_meters: int = Query(default=7000, ge=100, le=50000),
    session: Session = Depends(get_db),
) -> list[dict[str, object]]:
    if content_type_id is not None and content_type_id not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="지원하지 않는 장소 카테고리입니다.")
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="위도와 경도가 모두 필요합니다.")
    if latitude is not None and longitude is not None:
        _validate_coordinates(latitude, longitude)

    filters = []
    if content_type_id:
        filters.append(Place.content_type_id == content_type_id)
    if ids:
        try:
            place_ids = list(dict.fromkeys(int(value) for value in ids.split(",") if value.strip()))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="ids는 쉼표로 구분된 숫자여야 합니다.") from exc
        if len(place_ids) > 100:
            raise HTTPException(status_code=422, detail="한 번에 최대 100개의 장소를 조회할 수 있습니다.")
        filters.append(Place.id.in_(place_ids) if place_ids else Place.id == -1)
    elif latitude is None or longitude is None:
        raise HTTPException(status_code=422, detail="주변 장소 조회에는 현재 위치가 필요합니다.")

    if not ids and latitude is not None and longitude is not None:
        latitude_meters = (Place.latitude - latitude) * 111_320.0
        longitude_meters = (Place.longitude - longitude) * 88_000.0
        filters.append(
            latitude_meters * latitude_meters + longitude_meters * longitude_meters
            <= radius_meters * radius_meters
        )

    statement = select(Place).options(selectinload(Place.images)).where(*filters)
    if ids:
        statement = statement.order_by(Place.id.asc())
    else:
        latitude_delta = Place.latitude - float(latitude)
        longitude_delta = Place.longitude - float(longitude)
        statement = statement.order_by(
            (latitude_delta * latitude_delta + longitude_delta * longitude_delta).asc(), Place.id.asc()
        )

    places = session.scalars(statement).unique().all()
    return [
        {
            "id": place.id,
            "source": place.source,
            "content_type": place.content_type,
            "content_type_id": place.content_type_id,
            "title": place.title,
            "address": place.address,
            "longitude": place.longitude,
            "latitude": place.latitude,
            "image_url": image_url(place),
            "view_count": place.view_count,
            "like_count": place.like_count,
            "review_count": place.review_count,
            "average_rating": round(place.rating_sum / place.review_count, 1) if place.review_count else 0.0,
            "distance_meters": (
                round(haversine_meters(latitude, longitude, place.latitude, place.longitude), 1)
                if latitude is not None and longitude is not None
                else None
            ),
        }
        for place in places
    ]


@router.get("/duplicate-check", response_model=DuplicateCheckResponse)
def check_duplicate_place(
    title: str = Query(min_length=1, max_length=300),
    latitude: float = Query(),
    longitude: float = Query(),
    exclude_place_id: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    _validate_coordinates(latitude, longitude)
    candidates = find_duplicate_places(
        session,
        title=title,
        latitude=latitude,
        longitude=longitude,
        exclude_place_id=exclude_place_id,
    )
    return {
        "has_duplicates": bool(candidates),
        "radius_meters": DUPLICATE_RADIUS_METERS,
        "candidates": candidates,
    }


@router.post("", response_model=PlaceDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_place(
    title: str = Form(min_length=1, max_length=300),
    content_type_id: str = Form(),
    description: str = Form(min_length=1, max_length=10_000),
    latitude: float = Form(),
    longitude: float = Form(),
    password: str = Form(min_length=1, max_length=200),
    tags: str = Form(default=""),
    address: str = Form(default="", max_length=500),
    detail_address: str = Form(default="", max_length=500),
    allow_duplicate: bool = Form(default=False),
    images: list[UploadFile] | None = File(default=None),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _validate_coordinates(latitude, longitude)
    if content_type_id not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="지원하지 않는 장소 카테고리입니다.")
    if not password.strip():
        raise HTTPException(status_code=422, detail="비밀번호는 공백으로만 구성할 수 없습니다.")
    normalized_title = title.strip()
    normalized_description = description.strip()
    if not normalized_title or not normalized_description:
        raise HTTPException(status_code=422, detail="장소명과 설명은 공백으로만 구성할 수 없습니다.")

    candidates = find_duplicate_places(
        session, title=normalized_title, latitude=latitude, longitude=longitude
    )
    if candidates and not allow_duplicate:
        raise _duplicate_warning(candidates)

    normalized_address = address.strip()
    zipcode = ""
    if not normalized_address and settings.kakao_rest_api_key.strip():
        try:
            geocoded = await reverse_geocode(settings, latitude, longitude)
        except KakaoLocalError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if geocoded:
            normalized_address = geocoded["address"]
            zipcode = geocoded["zipcode"]

    uploaded_images = await read_uploaded_images(images)
    place = Place(
        content_id=None,
        source="user",
        region="서울",
        content_type=SUPPORTED_CONTENT_TYPES[content_type_id],
        content_type_id=content_type_id,
        title=normalized_title,
        description=normalized_description,
        address=normalized_address,
        detail_address=detail_address.strip(),
        address_source="user" if address.strip() else ("kakao_reverse" if normalized_address else "missing"),
        zipcode=zipcode,
        longitude=longitude,
        latitude=latitude,
        password=password,
    )
    session.add(place)
    session.flush()
    replace_place_tags(session, place, parse_tags(tags))
    append_images(place, uploaded_images)
    await _refresh_user_place_profile(session, settings, place)
    session.commit()
    return serialize_place_detail(_get_place(session, place.id))


@router.get("/{place_id}", response_model=PlaceDetailResponse)
async def get_place(
    place_id: int,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    place = _get_place(session, place_id)
    if not place.address and settings.kakao_rest_api_key.strip():
        try:
            geocoded = await reverse_geocode(settings, place.latitude, place.longitude)
        except KakaoLocalError:
            geocoded = None
        if geocoded:
            place.address = geocoded["address"]
            place.zipcode = geocoded["zipcode"]
            place.address_source = "kakao_reverse"
            session.commit()
    fingerprint = request_fingerprint(request, settings)
    liked = session.scalar(
        select(PlaceLike.id).where(
            PlaceLike.place_id == place_id, PlaceLike.fingerprint_hash == fingerprint
        )
    ) is not None
    return serialize_place_detail(place, liked_by_me=liked)


@router.put("/{place_id}", response_model=PlaceDetailResponse)
async def update_place(
    place_id: int,
    password: str = Form(min_length=1, max_length=200),
    title: str | None = Form(default=None, min_length=1, max_length=300),
    content_type_id: str | None = Form(default=None),
    description: str | None = Form(default=None, min_length=1, max_length=10_000),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    tags: str | None = Form(default=None),
    address: str | None = Form(default=None, max_length=500),
    detail_address: str | None = Form(default=None, max_length=500),
    allow_duplicate: bool = Form(default=False),
    images: list[UploadFile] | None = File(default=None),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    place = _get_place(session, place_id)
    require_user_place_password(place, password)
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="좌표 수정에는 위도와 경도가 모두 필요합니다.")
    new_latitude = latitude if latitude is not None else place.latitude
    new_longitude = longitude if longitude is not None else place.longitude
    _validate_coordinates(new_latitude, new_longitude)
    new_title = title.strip() if title is not None else place.title
    if not new_title:
        raise HTTPException(status_code=422, detail="장소명은 공백으로만 구성할 수 없습니다.")
    if description is not None and not description.strip():
        raise HTTPException(status_code=422, detail="설명은 공백으로만 구성할 수 없습니다.")

    if title is not None or latitude is not None:
        candidates = find_duplicate_places(
            session,
            title=new_title,
            latitude=new_latitude,
            longitude=new_longitude,
            exclude_place_id=place.id,
        )
        if candidates and not allow_duplicate:
            raise _duplicate_warning(candidates)

    if content_type_id is not None:
        if content_type_id not in SUPPORTED_CONTENT_TYPES:
            raise HTTPException(status_code=422, detail="지원하지 않는 장소 카테고리입니다.")
        place.content_type_id = content_type_id
        place.content_type = SUPPORTED_CONTENT_TYPES[content_type_id]
    if title is not None:
        place.title = new_title
    if description is not None:
        place.description = description.strip()
    if latitude is not None and longitude is not None:
        place.latitude = latitude
        place.longitude = longitude
    if address is not None:
        place.address = address.strip()
        place.address_source = "user" if place.address else "missing"
    if detail_address is not None:
        place.detail_address = detail_address.strip()

    if (
        latitude is not None
        and longitude is not None
        and (address is None or not address.strip())
        and settings.kakao_rest_api_key.strip()
    ):
        try:
            geocoded = await reverse_geocode(settings, latitude, longitude)
        except KakaoLocalError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if geocoded:
            place.address = geocoded["address"]
            place.zipcode = geocoded["zipcode"]
            place.address_source = "kakao_reverse"
    if tags is not None:
        replace_place_tags(session, place, parse_tags(tags))

    append_images(place, await read_uploaded_images(images))
    await _refresh_user_place_profile(session, settings, place)
    session.commit()
    return serialize_place_detail(_get_place(session, place.id))


@router.delete("/{place_id}", response_model=DeleteResponse)
async def delete_place(
    place_id: int,
    payload: PasswordRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    place = _get_place(session, place_id)
    require_user_place_password(place, payload.password)
    try:
        await run_in_threadpool(delete_place_vectors, settings, place_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="장소 벡터를 삭제하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        ) from exc
    for association in place.place_tags:
        association.tag.usage_count = max(0, association.tag.usage_count - 1)
    session.delete(place)
    session.commit()
    return {"deleted": True, "id": place_id}


@router.get("/{place_id}/images/{image_id}")
def get_place_image(place_id: int, image_id: int, session: Session = Depends(get_db)) -> Response:
    image = session.scalar(
        select(PlaceImage).where(PlaceImage.id == image_id, PlaceImage.place_id == place_id)
    )
    if image is None:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    return Response(
        content=image.data,
        media_type=image.media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.delete("/{place_id}/images/{image_id}", response_model=DeleteResponse)
def delete_place_image(
    place_id: int,
    image_id: int,
    payload: PasswordRequest,
    session: Session = Depends(get_db),
) -> dict[str, object]:
    place = _get_place(session, place_id)
    require_user_place_password(place, payload.password)
    image = next((item for item in place.images if item.id == image_id), None)
    if image is None:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    session.delete(image)
    session.commit()
    return {"deleted": True, "id": image_id}
