import asyncio
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.db.models import Place
from app.services.kakao_local import KakaoLocalError
from app.services.travel_course_addresses import enrich_travel_course_addresses


def _place(
    content_id: str,
    *,
    content_type_id: str = "25",
    address: str = "",
    latitude: float,
    longitude: float,
) -> Place:
    return Place(
        content_id=content_id,
        source="dataset",
        region="서울",
        content_type="여행코스" if content_type_id == "25" else "관광지",
        content_type_id=content_type_id,
        title=content_id,
        address=address,
        address_source="dataset" if address else "missing",
        latitude=latitude,
        longitude=longitude,
    )


def test_enrichment_updates_only_empty_travel_courses_and_reuses_coordinates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'addresses.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    calls: Counter[tuple[float, float]] = Counter()

    async def fake_reverse(_settings, latitude: float, longitude: float):
        coordinate = (latitude, longitude)
        calls[coordinate] += 1
        if coordinate == (37.6, 127.1):
            raise KakaoLocalError("temporary failure")
        return {
            "address": "서울특별시 종로구 테스트로 1",
            "road_address": "서울특별시 종로구 테스트로 1",
            "lot_address": "서울특별시 종로구 테스트동 1",
            "zipcode": "01234",
        }

    monkeypatch.setattr(
        "app.services.travel_course_addresses.reverse_geocode",
        fake_reverse,
    )
    with Session(engine) as session:
        session.add_all(
            [
                _place("course-1", latitude=37.5, longitude=127.0),
                _place("course-2", latitude=37.5, longitude=127.0),
                _place("course-failure", latitude=37.6, longitude=127.1),
                _place("course-existing", address="서울특별시 중구", latitude=37.7, longitude=127.2),
                _place("tourist-empty", content_type_id="12", latitude=37.8, longitude=127.3),
            ]
        )
        session.commit()

        report = asyncio.run(
            enrich_travel_course_addresses(
                session,
                Settings(_env_file=None, kakao_rest_api_key="test-key"),
                max_concurrency=2,
                max_attempts=3,
                retry_delay_seconds=0,
            )
        )
        places = {
            place.content_id: place
            for place in session.scalars(select(Place)).all()
        }

    assert report.candidates == 3
    assert report.unique_coordinates == 2
    assert report.updated_places == 2
    assert report.failed_coordinates == 1
    assert calls[(37.5, 127.0)] == 1
    assert calls[(37.6, 127.1)] == 3
    assert places["course-1"].address == "서울특별시 종로구 테스트로 1"
    assert places["course-2"].zipcode == "01234"
    assert places["course-2"].address_source == "kakao_reverse"
    assert places["course-failure"].address == ""
    assert places["course-existing"].address == "서울특별시 중구"
    assert places["tourist-empty"].address == ""


def test_enrichment_without_key_is_non_blocking(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'missing-key.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.add(_place("course", latitude=37.5, longitude=127.0))
        session.commit()
        report = asyncio.run(
            enrich_travel_course_addresses(
                session,
                Settings(_env_file=None, kakao_rest_api_key=""),
            )
        )

    assert report.skipped_missing_key is True
    assert report.updated_places == 0
    assert report.failed_coordinates == 1
