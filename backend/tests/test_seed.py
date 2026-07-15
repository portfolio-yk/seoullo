import json
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Place, PlaceEmotionProfile
from app.services.seed import inspect_dataset, seed_dataset


def write_sample(path: Path) -> None:
    document = {
        "region": "서울",
        "contentType": "관광지",
        "contentTypeId": "12",
        "total": 2,
        "items": [
            {
                "contentid": "sample-1",
                "contenttypeid": "12",
                "title": "샘플 장소",
                "addr1": "서울특별시",
                "addr2": "",
                "mapx": "126.9780",
                "mapy": "37.5665",
                "firstimage": "",
                "firstimage2": "",
                "emotion": {
                    "mood": {"지침": 4, "불안": 2, "답답함": 4, "설렘": 2, "외로움": 2, "평온함": 5},
                    "afterFeeling": {"회복": 5, "해방": 3, "활력": 2, "위로": 2, "몰입": 1, "설렘": 2},
                    "style": {"조용히 혼자": 4, "가볍게 산책": 5, "새로운 자극": 2, "누군가와 함께": 4},
                },
            },
            {
                "contentid": "sample-2",
                "contenttypeid": "12",
                "title": "주소 없는 장소",
                "addr1": "",
                "addr2": "",
                "mapx": "127.0000",
                "mapy": "37.5000",
                "firstimage": "",
                "firstimage2": "",
            },
        ],
    }
    (path / "서울_관광지.json").write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")


def test_seed_is_idempotent(tmp_path: Path) -> None:
    write_sample(tmp_path)
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        first = seed_dataset(session, tmp_path)
        second = seed_dataset(session, tmp_path)
        count = session.scalar(select(func.count(Place.id)))
        profile_count = session.scalar(select(func.count(PlaceEmotionProfile.place_id)))

    assert first.inserted_items == 2
    assert second.inserted_items == 0
    assert second.skipped_items == 2
    assert count == 2
    assert profile_count == 1
    assert first.emotion_profiles_inserted == 1
    assert first.missing_emotion_items == 1
    assert second.emotion_profiles_inserted == 0


def test_missing_address_is_preserved_for_lazy_geocoding(tmp_path: Path) -> None:
    write_sample(tmp_path)
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        seed_dataset(session, tmp_path)
        place = session.scalar(select(Place).where(Place.content_id == "sample-2"))

    assert place is not None
    assert place.address == ""
    assert place.address_source == "missing"


def test_new_emotion_data_supplements_an_existing_place(tmp_path: Path) -> None:
    write_sample(tmp_path)
    engine = create_engine(f"sqlite:///{(tmp_path / 'supplement.db').as_posix()}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        seed_dataset(session, tmp_path)

    data_path = next(tmp_path.glob("*.json"))
    document = json.loads(data_path.read_text(encoding="utf-8"))
    document["items"][1]["emotion"] = document["items"][0]["emotion"]
    data_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")

    with Session(engine) as session:
        report = seed_dataset(session, tmp_path)
        profile_count = session.scalar(select(func.count(PlaceEmotionProfile.place_id)))

    assert report.inserted_items == 0
    assert report.emotion_profiles_inserted == 1
    assert report.missing_emotion_items == 0
    assert profile_count == 2


def test_inventory_reports_unavailable_categories(tmp_path: Path) -> None:
    write_sample(tmp_path)
    report = inspect_dataset(tmp_path)

    assert report.discovered_items == 2
    assert report.invalid_items == 0
    assert report.missing_emotion_items == 1
    assert report.invalid_emotion_items == 0
    assert "레포츠" in report.missing_content_types
