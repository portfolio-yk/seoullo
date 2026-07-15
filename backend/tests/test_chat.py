from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.chat import router as chat_router
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.models import Place
from app.db.session import get_db
from app.services.chat import GeneratedChatAnswer, generate_grounded_answer, retrieve_places


def _add_places(session: Session) -> None:
    session.add_all(
        [
            Place(
                content_id="festival-1",
                source="dataset",
                region="서울",
                content_type="축제공연행사",
                content_type_id="15",
                title="종로 문화 축제",
                description="종로에서 열리는 문화 행사",
                address="서울특별시 종로구",
                longitude=126.98,
                latitude=37.57,
                like_count=10,
            ),
            Place(
                content_id="culture-1",
                source="dataset",
                region="서울",
                content_type="문화시설",
                content_type_id="14",
                title="마포 미술관",
                description="전시를 볼 수 있는 문화 공간",
                address="서울특별시 마포구",
                longitude=126.91,
                latitude=37.55,
                like_count=4,
            ),
            Place(
                content_id=None,
                source="user",
                region="서울",
                content_type="쇼핑",
                content_type_id="38",
                title="커뮤니티 상점",
                description="사용자가 등록한 상점",
                address="서울특별시 강남구",
                longitude=127.03,
                latitude=37.50,
                password="password",
                like_count=2,
            ),
        ]
    )
    session.commit()


def test_sqlite_retrieval_understands_category_district_and_community(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'chat.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        _add_places(session)

        festivals, method = retrieve_places(
            session,
            Settings(_env_file=None, openai_api_key="", pinecone_api_key=""),
            "종로구 축제 알려줘",
        )
        community, community_method = retrieve_places(
            session,
            Settings(_env_file=None, openai_api_key="", pinecone_api_key=""),
            "커뮤니티 장소 찾아줘",
        )

    assert method == "sqlite_keyword"
    assert [place.title for place in festivals] == ["종로 문화 축제"]
    assert community_method == "sqlite_keyword"
    assert [place.title for place in community] == ["커뮤니티 상점"]


def test_structured_answer_rejects_unretrieved_citations(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'answer.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        _add_places(session)
        places, _ = retrieve_places(
            session,
            Settings(_env_file=None, openai_api_key="", pinecone_api_key=""),
            "종로구 축제",
        )

        class FakeResponses:
            def parse(self, **_kwargs):
                return SimpleNamespace(
                    output_parsed=GeneratedChatAnswer(
                        answer="종로 문화 축제를 확인해 보세요.",
                        cited_place_ids=[places[0].id],
                    )
                )

        answer, cited_ids, source = generate_grounded_answer(
            Settings(_env_file=None, openai_api_key="test-key"),
            "종로구 축제",
            [],
            places,
            client=SimpleNamespace(responses=FakeResponses()),
        )

    assert answer == "종로 문화 축제를 확인해 보세요."
    assert cited_ids == [places[0].id]
    assert source == "openai"


def test_chat_api_returns_grounded_sources_without_persisting_history(tmp_path: Path) -> None:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'api.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with testing_session() as session:
        _add_places(session)

    def override_db():
        with testing_session() as session:
            yield session

    app = FastAPI()
    app.include_router(chat_router, prefix="/api")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        openai_api_key="",
        pinecone_api_key="",
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/chat/messages",
            json={
                "message": "종로구 축제 알려줘",
                "history": [{"role": "user", "content": "서울 여행 중이야"}],
            },
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["retrieval_method"] == "sqlite_keyword"
    assert payload["answer_source"] == "rule"
    assert payload["sources"][0]["title"] == "종로 문화 축제"
