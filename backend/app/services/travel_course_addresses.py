from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Place
from app.services.kakao_local import KakaoLocalError, reverse_geocode


logger = logging.getLogger(__name__)


@dataclass
class TravelCourseAddressReport:
    candidates: int
    unique_coordinates: int
    updated_places: int
    failed_coordinates: int
    skipped_missing_key: bool = False

    def to_dict(self) -> dict[str, int | bool]:
        return asdict(self)


async def _resolve_coordinate(
    settings: Settings,
    latitude: float,
    longitude: float,
    *,
    semaphore: asyncio.Semaphore,
    max_attempts: int,
    retry_delay_seconds: float,
) -> dict[str, str] | None:
    async with semaphore:
        for attempt in range(max_attempts):
            try:
                result = await reverse_geocode(settings, latitude, longitude)
                if result and result.get("address", "").strip():
                    return result
                return None
            except KakaoLocalError:
                if attempt + 1 >= max_attempts:
                    return None
                await asyncio.sleep(retry_delay_seconds * (2**attempt))
    return None


async def enrich_travel_course_addresses(
    session: Session,
    settings: Settings,
    *,
    max_concurrency: int = 4,
    max_attempts: int = 3,
    retry_delay_seconds: float = 0.3,
) -> TravelCourseAddressReport:
    places = list(
        session.scalars(
            select(Place).where(
                Place.content_type_id == "25",
                Place.address == "",
            )
        )
    )
    coordinate_groups: dict[tuple[float, float], list[Place]] = {}
    for place in places:
        coordinate_groups.setdefault((place.latitude, place.longitude), []).append(place)

    if not places:
        return TravelCourseAddressReport(0, 0, 0, 0)
    if not settings.kakao_rest_api_key.strip():
        logger.warning("여행코스 주소 보강을 건너뜁니다: KAKAO_REST_API_KEY가 없습니다.")
        return TravelCourseAddressReport(
            candidates=len(places),
            unique_coordinates=len(coordinate_groups),
            updated_places=0,
            failed_coordinates=len(coordinate_groups),
            skipped_missing_key=True,
        )

    semaphore = asyncio.Semaphore(max(1, max_concurrency))
    coordinates = list(coordinate_groups)
    results = await asyncio.gather(
        *(
            _resolve_coordinate(
                settings,
                latitude,
                longitude,
                semaphore=semaphore,
                max_attempts=max(1, max_attempts),
                retry_delay_seconds=max(0.0, retry_delay_seconds),
            )
            for latitude, longitude in coordinates
        )
    )

    updated_places = 0
    failed_coordinates = 0
    for coordinate, result in zip(coordinates, results, strict=True):
        if result is None:
            failed_coordinates += 1
            logger.warning(
                "여행코스 역지오코딩 실패: latitude=%s longitude=%s",
                coordinate[0],
                coordinate[1],
            )
            continue
        for place in coordinate_groups[coordinate]:
            place.address = result["address"].strip()
            place.zipcode = result.get("zipcode", "").strip()
            place.address_source = "kakao_reverse"
            updated_places += 1

    session.commit()
    return TravelCourseAddressReport(
        candidates=len(places),
        unique_coordinates=len(coordinate_groups),
        updated_places=updated_places,
        failed_coordinates=failed_coordinates,
    )
