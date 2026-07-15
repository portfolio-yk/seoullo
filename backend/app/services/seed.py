from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.constants import REQUIRED_DATASET_CONTENT_TYPE_IDS, SUPPORTED_CONTENT_TYPES
from app.core.emotions import EmotionValidationError, validate_emotion_payload
from app.db.models import DataSource, Place, PlaceEmotionProfile


@dataclass
class SeedReport:
    files: int
    discovered_items: int
    inserted_items: int
    skipped_items: int
    invalid_items: int
    emotion_profiles_inserted: int
    missing_emotion_items: int
    invalid_emotion_items: int
    content_types: dict[str, int]
    missing_content_types: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_document(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        document = json.load(file)
    if not isinstance(document.get("items"), list):
        raise ValueError(f"items 배열이 없는 데이터 파일입니다: {path.name}")
    return document


def _text(item: dict[str, Any], key: str) -> str:
    value = item.get(key, "")
    return "" if value is None else str(value).strip()


def _coordinate(item: dict[str, Any], key: str) -> float:
    value = _text(item, key)
    if not value:
        raise ValueError(f"좌표 필드 {key}가 비어 있습니다.")
    return float(value)


def _place_from_item(document: dict[str, Any], item: dict[str, Any]) -> Place:
    address = _text(item, "addr1")
    content_type_id = _text(item, "contenttypeid") or str(document.get("contentTypeId") or "")
    return Place(
        content_id=_text(item, "contentid"),
        source="dataset",
        region=str(document.get("region") or "서울"),
        content_type=str(document.get("contentType") or SUPPORTED_CONTENT_TYPES.get(content_type_id, "기타")),
        content_type_id=content_type_id,
        title=_text(item, "title"),
        description="",
        address=address,
        detail_address=_text(item, "addr2"),
        address_source="dataset" if address else "missing",
        zipcode=_text(item, "zipcode"),
        telephone=_text(item, "tel"),
        longitude=_coordinate(item, "mapx"),
        latitude=_coordinate(item, "mapy"),
        map_level=_text(item, "mlevel"),
        area_code=_text(item, "areacode"),
        sigungu_code=_text(item, "sigungucode"),
        legal_dong_region_code=_text(item, "lDongRegnCd"),
        legal_dong_sigungu_code=_text(item, "lDongSignguCd"),
        category1=_text(item, "cat1"),
        category2=_text(item, "cat2"),
        category3=_text(item, "cat3"),
        classification1=_text(item, "lclsSystm1"),
        classification2=_text(item, "lclsSystm2"),
        classification3=_text(item, "lclsSystm3"),
        primary_image_url=_text(item, "firstimage"),
        thumbnail_url=_text(item, "firstimage2"),
        copyright_code=_text(item, "cpyrhtDivCd"),
        source_created_time=_text(item, "createdtime"),
        source_modified_time=_text(item, "modifiedtime"),
    )


def _emotion_values(item: dict[str, Any]) -> tuple[dict[str, int] | None, str | None]:
    if "emotion" not in item:
        return None, "missing"
    try:
        return validate_emotion_payload(item["emotion"]), None
    except EmotionValidationError:
        return None, "invalid"


def ensure_data_source(session: Session) -> None:
    source = session.scalar(select(DataSource).where(DataSource.region == "서울"))
    if source is not None:
        return
    session.add(
        DataSource(
            region="서울",
            provider="한국관광공사",
            dataset_name="국문 관광정보 서비스(TourAPI 4.0)",
            source_url="https://www.data.go.kr/data/15101578/openapi.do",
            license_name="공공누리 제1유형",
            license_url="https://www.kogl.or.kr/info/licenseTypeView.do?licenseType=1",
            notice="출처 표시 필수, 원본 데이터 내용 변경 금지",
        )
    )


def seed_dataset(session: Session, data_dir: Path) -> SeedReport:
    if not data_dir.exists():
        raise FileNotFoundError(f"서울 데이터 디렉터리를 찾을 수 없습니다: {data_dir}")

    paths = sorted(data_dir.glob("서울_*.json"))
    existing_places = {
        place.content_id: place
        for place in session.scalars(
            select(Place)
            .where(Place.content_id.is_not(None))
            .options(selectinload(Place.emotion_profile))
        )
    }
    discovered_items = inserted_items = skipped_items = invalid_items = 0
    emotion_profiles_inserted = missing_emotion_items = invalid_emotion_items = 0
    content_types: dict[str, int] = {}
    discovered_type_ids: set[str] = set()

    ensure_data_source(session)

    for path in paths:
        document = _read_document(path)
        type_id = str(document.get("contentTypeId") or "")
        type_name = str(document.get("contentType") or SUPPORTED_CONTENT_TYPES.get(type_id, "기타"))
        discovered_type_ids.add(type_id)
        items = document["items"]
        discovered_items += len(items)
        content_types[type_name] = content_types.get(type_name, 0) + len(items)

        for item in items:
            content_id = _text(item, "contentid")
            emotion_values, emotion_error = _emotion_values(item)
            if emotion_error == "missing":
                missing_emotion_items += 1
            elif emotion_error == "invalid":
                invalid_emotion_items += 1

            existing = existing_places.get(content_id)
            if not content_id or existing is not None:
                skipped_items += 1
                if existing is not None and emotion_values is not None and existing.emotion_profile is None:
                    existing.emotion_profile = PlaceEmotionProfile(**emotion_values)
                    emotion_profiles_inserted += 1
                continue

            try:
                place = _place_from_item(document, item)
            except (TypeError, ValueError):
                invalid_items += 1
                continue
            if not place.title or not place.content_type_id:
                invalid_items += 1
                continue
            if emotion_values is not None:
                place.emotion_profile = PlaceEmotionProfile(**emotion_values)
                emotion_profiles_inserted += 1
            session.add(place)
            existing_places[content_id] = place
            inserted_items += 1

    session.commit()
    missing = [
        SUPPORTED_CONTENT_TYPES[code]
        for code in sorted(REQUIRED_DATASET_CONTENT_TYPE_IDS)
        if code not in discovered_type_ids
    ]
    return SeedReport(
        files=len(paths),
        discovered_items=discovered_items,
        inserted_items=inserted_items,
        skipped_items=skipped_items,
        invalid_items=invalid_items,
        emotion_profiles_inserted=emotion_profiles_inserted,
        missing_emotion_items=missing_emotion_items,
        invalid_emotion_items=invalid_emotion_items,
        content_types=content_types,
        missing_content_types=missing,
    )


def dataset_place_count(session: Session) -> int:
    return session.scalar(select(func.count(Place.id)).where(Place.source == "dataset")) or 0


def seed_if_empty(session: Session, data_dir: Path) -> SeedReport | None:
    if dataset_place_count(session) > 0:
        return None
    return seed_dataset(session, data_dir)


def inspect_dataset(data_dir: Path) -> SeedReport:
    paths = sorted(data_dir.glob("서울_*.json"))
    discovered_items = invalid_items = 0
    missing_emotion_items = invalid_emotion_items = 0
    content_types: dict[str, int] = {}
    discovered_type_ids: set[str] = set()

    for path in paths:
        document = _read_document(path)
        type_id = str(document.get("contentTypeId") or "")
        type_name = str(document.get("contentType") or SUPPORTED_CONTENT_TYPES.get(type_id, "기타"))
        discovered_type_ids.add(type_id)
        items = document["items"]
        discovered_items += len(items)
        content_types[type_name] = content_types.get(type_name, 0) + len(items)
        for item in items:
            try:
                _coordinate(item, "mapx")
                _coordinate(item, "mapy")
            except (TypeError, ValueError):
                invalid_items += 1
            _, emotion_error = _emotion_values(item)
            if emotion_error == "missing":
                missing_emotion_items += 1
            elif emotion_error == "invalid":
                invalid_emotion_items += 1

    missing = [
        SUPPORTED_CONTENT_TYPES[code]
        for code in sorted(REQUIRED_DATASET_CONTENT_TYPE_IDS)
        if code not in discovered_type_ids
    ]
    return SeedReport(
        files=len(paths),
        discovered_items=discovered_items,
        inserted_items=0,
        skipped_items=0,
        invalid_items=invalid_items,
        emotion_profiles_inserted=0,
        missing_emotion_items=missing_emotion_items,
        invalid_emotion_items=invalid_emotion_items,
        content_types=content_types,
        missing_content_types=missing,
    )
