import io
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.places import router as places_router
from app.api.interactions import router as interactions_router
from app.api.reviews import router as reviews_router
from app.api.tags import router as tags_router
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.core.emotions import EMOTION_COLUMNS
from app.db.models import Place
from app.db.session import get_db


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'places.db').as_posix()}", connect_args={"check_same_thread": False}
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with testing_session() as session:
        session.add(
            Place(
                content_id="dataset-1",
                source="dataset",
                region="서울",
                content_type="관광지",
                content_type_id="12",
                title="테스트 공원",
                description="",
                address="서울특별시 중구",
                address_source="dataset",
                longitude=126.9780,
                latitude=37.5665,
            )
        )
        session.commit()

    def override_db():
        with testing_session() as session:
            yield session

    app = FastAPI()
    app.include_router(places_router, prefix="/api")
    app.include_router(reviews_router, prefix="/api")
    app.include_router(interactions_router, prefix="/api")
    app.include_router(tags_router, prefix="/api")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        kakao_rest_api_key="",
        openai_api_key="test-openai",
        pinecone_api_key="test-pinecone",
    )
    monkeypatch.setattr(
        "app.api.places.generate_place_emotion_values",
        lambda _settings, _context: {column: 3 for column in EMOTION_COLUMNS},
    )
    lexical_syncs: list[tuple[int, list[str]]] = []
    monkeypatch.setattr("app.api.places.sync_place_vectors", lambda *_args: None)
    monkeypatch.setattr(
        "app.api.places.upsert_lexical_place",
        lambda _settings, place: lexical_syncs.append(
            (place.id, [association.tag.name for association in place.place_tags])
        ),
    )
    monkeypatch.setattr("app.api.places.delete_place_vectors", lambda *_args: None)
    app.state.testing_session = testing_session
    app.state.lexical_syncs = lexical_syncs
    with TestClient(app) as test_client:
        yield test_client


def test_list_search_categories_and_distance_validation(client: TestClient) -> None:
    response = client.get("/api/places", params={"q": "테스트"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "테스트 공원"

    categories = client.get("/api/places/categories")
    assert categories.status_code == 200
    assert next(item for item in categories.json() if item["content_type_id"] == "12")["count"] == 1
    assert "39" not in {item["content_type_id"] for item in categories.json()}

    invalid_distance = client.get("/api/places", params={"sort": "distance"})
    assert invalid_distance.status_code == 422

    outside_radius = client.get(
        "/api/places",
        params={"latitude": 37.0, "longitude": 127.0, "radius_meters": 1000},
    )
    assert outside_radius.status_code == 200
    assert outside_radius.json()["total"] == 0


def test_food_category_is_not_supported(client: TestClient) -> None:
    response = client.post(
        "/api/places",
        data={
            "title": "음식점 테스트",
            "content_type_id": "39",
            "description": "지원하지 않는 카테고리",
            "latitude": "37.5665",
            "longitude": "126.9780",
            "password": "password",
        },
    )
    assert response.status_code == 422


def test_user_place_crud_duplicate_warning_images_and_tag_search(client: TestClient) -> None:
    create_data = {
        "title": "테스트 공원",
        "content_type_id": "12",
        "description": "사용자가 발견한 장소",
        "latitude": "37.5665",
        "longitude": "126.9780",
        "password": "plain-password",
        "tags": '["숨은명소", "산책"]',
    }

    warning = client.post("/api/places", data=create_data)
    assert warning.status_code == 409
    assert warning.json()["detail"]["code"] == "DUPLICATE_PLACE_WARNING"

    png = b"\x89PNG\r\n\x1a\n" + b"test-image"
    created = client.post(
        "/api/places",
        data={**create_data, "allow_duplicate": "true"},
        files={"images": ("place.png", io.BytesIO(png), "image/png")},
    )
    assert created.status_code == 201, created.text
    place = created.json()
    place_id = place["id"]
    image_id = place["images"][0]["id"]
    assert place["source"] == "user"
    assert place["tags"] == ["숨은명소", "산책"]
    assert place["image_url"].endswith(f"/{image_id}")

    image = client.get(f"/api/places/{place_id}/images/{image_id}")
    assert image.status_code == 200
    assert image.content == png
    assert image.headers["content-type"] == "image/png"

    tag_search = client.get("/api/places", params={"q": "#숨은명소"})
    assert tag_search.status_code == 200
    assert tag_search.json()["total"] == 1

    wrong_password = client.put(
        f"/api/places/{place_id}", data={"password": "wrong", "title": "수정 실패"}
    )
    assert wrong_password.status_code == 403

    updated = client.put(
        f"/api/places/{place_id}",
        data={"password": "plain-password", "title": "수정된 장소", "tags": "야경,산책"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "수정된 장소"
    assert updated.json()["tags"] == ["야경", "산책"]

    protected_dataset = client.request(
        "DELETE", "/api/places/1", json={"password": "anything"}
    )
    assert protected_dataset.status_code == 403

    deleted_image = client.request(
        "DELETE",
        f"/api/places/{place_id}/images/{image_id}",
        json={"password": "plain-password"},
    )
    assert deleted_image.status_code == 200

    deleted = client.request(
        "DELETE", f"/api/places/{place_id}", json={"password": "plain-password"}
    )
    assert deleted.status_code == 200
    assert client.get(f"/api/places/{place_id}").status_code == 404


def test_rejects_disguised_and_oversized_images(client: TestClient) -> None:
    data = {
        "title": "이미지 테스트",
        "content_type_id": "14",
        "description": "잘못된 이미지 검증",
        "latitude": "37.55",
        "longitude": "127.01",
        "password": "password",
    }
    disguised = client.post(
        "/api/places",
        data=data,
        files={"images": ("fake.png", io.BytesIO(b"not-a-png"), "image/png")},
    )
    assert disguised.status_code == 415

    oversized = b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024)
    too_large = client.post(
        "/api/places",
        data=data,
        files={"images": ("large.png", io.BytesIO(oversized), "image/png")},
    )
    assert too_large.status_code == 413


def test_reviews_likes_views_and_counters(client: TestClient) -> None:
    headers = {"x-forwarded-for": "203.0.113.10", "user-agent": "Seoullo-Test-Browser"}

    first_view = client.post("/api/places/1/view")
    second_view = client.post("/api/places/1/view")
    assert first_view.json()["view_count"] == 1
    assert second_view.json()["view_count"] == 2

    liked = client.post("/api/places/1/like", headers=headers)
    unliked = client.post("/api/places/1/like", headers=headers)
    assert liked.json() == {"liked": True, "like_count": 1}
    assert unliked.json() == {"liked": False, "like_count": 0}

    created = client.post(
        "/api/places/1/reviews",
        headers=headers,
        json={"rating": 5, "content": "산책하기 좋아요.", "password": "review-password"},
    )
    assert created.status_code == 201, created.text
    review_id = created.json()["id"]
    assert "fingerprint_hash" not in created.json()

    duplicate = client.post(
        "/api/places/1/reviews",
        headers=headers,
        json={"rating": 4, "content": "두 번째 리뷰", "password": "another"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "장소당 리뷰를 하나만 작성할 수 있습니다. 기존 리뷰를 수정해 주세요."

    review_like = client.post(f"/api/reviews/{review_id}/like", headers=headers)
    assert review_like.json() == {"liked": True, "like_count": 1}
    reviews = client.get("/api/places/1/reviews", headers=headers)
    assert reviews.status_code == 200
    assert reviews.json()["items"][0]["liked_by_me"] is True

    wrong_password = client.put(
        f"/api/reviews/{review_id}",
        headers=headers,
        json={"rating": 3, "content": "수정", "password": "wrong"},
    )
    assert wrong_password.status_code == 403
    updated = client.put(
        f"/api/reviews/{review_id}",
        headers=headers,
        json={"rating": 3, "content": "조용한 시간에 추천해요.", "password": "review-password"},
    )
    assert updated.status_code == 200
    assert updated.json()["rating"] == 3

    place = client.get("/api/places/1", headers=headers).json()
    assert place["review_count"] == 1
    assert place["average_rating"] == 3.0
    assert place["view_count"] == 2

    deleted = client.request(
        "DELETE", f"/api/reviews/{review_id}", json={"password": "review-password"}
    )
    assert deleted.status_code == 200
    place_after_delete = client.get("/api/places/1").json()
    assert place_after_delete["review_count"] == 0
    assert place_after_delete["average_rating"] == 0.0


def test_popular_tags_and_id_filter(client: TestClient) -> None:
    created = client.post(
        "/api/places",
        data={
            "title": "인기 태그 장소",
            "content_type_id": "38",
            "description": "태그 집계를 위한 장소",
            "latitude": "37.57",
            "longitude": "127.02",
            "password": "password",
            "tags": '["숨은명소", "야경"]',
        },
    )
    assert created.status_code == 201
    place_id = created.json()["id"]

    popular = client.get("/api/tags/popular")
    assert popular.status_code == 200
    assert [item["name"] for item in popular.json()] == ["숨은명소", "야경"]

    filtered = client.get("/api/places", params={"ids": f"1,{place_id},9999", "size": 100})
    assert filtered.status_code == 200
    assert {item["id"] for item in filtered.json()["items"]} == {1, place_id}


def test_any_place_accepts_tags_but_only_user_place_owner_can_delete(client: TestClient) -> None:
    dataset_added = client.post(
        "/api/places/1/tags",
        json={"tags": ["#한적함", "산책"]},
    )
    assert dataset_added.status_code == 200, dataset_added.text
    assert dataset_added.json()["tags"] == ["한적함", "산책"]
    assert client.app.state.lexical_syncs[-1] == (1, ["한적함", "산책"])

    too_long = client.post("/api/places/1/tags", json={"tags": ["일곱글자태그임"]})
    assert too_long.status_code == 422
    assert too_long.json()["detail"] == "태그는 6글자 이하여야 합니다."

    dataset_delete = client.request(
        "DELETE",
        "/api/places/1/tags/산책",
        json={"password": "anything"},
    )
    assert dataset_delete.status_code == 403

    created = client.post(
        "/api/places",
        data={
            "title": "사용자 태그 장소",
            "content_type_id": "12",
            "description": "태그 권한 테스트",
            "latitude": "37.58",
            "longitude": "127.02",
            "password": "place-password",
        },
    )
    assert created.status_code == 201, created.text
    place_id = created.json()["id"]

    user_added = client.post(
        f"/api/places/{place_id}/tags",
        json={"tags": ["야경", "데이트", "조용함"]},
    )
    assert user_added.status_code == 200
    assert user_added.json()["tags"] == ["야경", "데이트", "조용함"]

    wrong_password = client.request(
        "DELETE",
        f"/api/places/{place_id}/tags/데이트",
        json={"password": "wrong"},
    )
    assert wrong_password.status_code == 403
    deleted = client.request(
        "DELETE",
        f"/api/places/{place_id}/tags/데이트",
        json={"password": "place-password"},
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["tags"] == ["야경", "조용함"]
    assert client.app.state.lexical_syncs[-1] == (place_id, ["야경", "조용함"])


def test_map_points_returns_more_than_list_page_limit(client: TestClient) -> None:
    with client.app.state.testing_session() as session:
        session.add_all(
            Place(
                content_id=f"map-{index}",
                source="dataset",
                region="서울",
                content_type="관광지",
                content_type_id="12",
                title=f"지도 장소 {index}",
                longitude=126.978 + index * 0.00001,
                latitude=37.5665 + index * 0.00001,
            )
            for index in range(105)
        )
        session.commit()

    response = client.get(
        "/api/places/map-points",
        params={"latitude": 37.5665, "longitude": 126.978, "radius_meters": 7000},
    )
    assert response.status_code == 200, response.text
    assert len(response.json()) == 106


def test_map_points_id_filter_returns_only_recommendations(client: TestClient) -> None:
    response = client.get("/api/places/map-points", params={"ids": "1,9999"})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [1]
