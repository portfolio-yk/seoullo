from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.constants import SUPPORTED_CONTENT_TYPES
from app.db.models import Place, PlaceTag, Tag
from app.schemas.chat import ChatHistoryMessage
from app.services.places import image_url, place_tags


RetrievalMethod = Literal["pinecone_semantic", "sqlite_keyword", "sqlite_popular"]

CATEGORY_TERMS = {
    "12": ("관광지", "관광", "명소", "볼거리"),
    "14": ("문화시설", "문화", "미술관", "박물관", "공연장"),
    "15": ("축제", "공연", "행사", "이벤트"),
    "25": ("여행코스", "코스", "동선"),
    "28": ("레포츠", "스포츠", "체험", "액티비티"),
    "32": ("숙박", "호텔", "숙소", "게스트하우스"),
    "38": ("쇼핑", "시장", "백화점", "상점"),
}
SEOUL_DISTRICTS = (
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구",
    "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구",
    "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구",
)
STOP_WORDS = {
    "서울", "추천", "알려줘", "알려주세요", "어디", "어떤", "있는", "있어", "찾아줘",
    "장소", "곳", "여행", "가볼만한", "근처", "주변", "위치", "일정", "정보", "이번",
}


class GeneratedChatAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=1200)
    cited_place_ids: list[int] = Field(default_factory=list, max_length=5)


def _place_statement():
    return select(Place).options(
        selectinload(Place.images),
        selectinload(Place.place_tags).selectinload(PlaceTag.tag),
    )


def _query_filters(message: str) -> tuple[str | None, str | None, str | None]:
    category = next(
        (code for code, terms in CATEGORY_TERMS.items() if any(term in message for term in terms)),
        None,
    )
    district = next((name for name in SEOUL_DISTRICTS if name in message), None)
    source = "user" if any(term in message for term in ("커뮤니티", "사용자 등록", "새로 등록")) else None
    return category, district, source


def _search_tokens(message: str) -> list[str]:
    excluded = set(STOP_WORDS)
    excluded.update(SEOUL_DISTRICTS)
    for terms in CATEGORY_TERMS.values():
        excluded.update(terms)
    tokens = [token for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", message) if token not in excluded]
    return list(dict.fromkeys(tokens))[:6]


def _sqlite_retrieve(session: Session, message: str, limit: int = 5) -> tuple[list[Place], RetrievalMethod]:
    category, district, source = _query_filters(message)
    tokens = _search_tokens(message)

    statement = _place_statement()
    base_filters = []
    if category:
        base_filters.append(Place.content_type_id == category)
    if district:
        base_filters.append(Place.address.ilike(f"%{district}%"))
    if source:
        base_filters.append(Place.source == source)
    if base_filters:
        statement = statement.where(*base_filters)

    if tokens:
        token_filters = []
        for token in tokens:
            pattern = f"%{token}%"
            token_filters.extend(
                (
                    Place.title.ilike(pattern),
                    Place.description.ilike(pattern),
                    Place.address.ilike(pattern),
                    Place.detail_address.ilike(pattern),
                    Place.place_tags.any(PlaceTag.tag.has(Tag.name.ilike(pattern))),
                )
            )
        statement = statement.where(or_(*token_filters))

    average_rating = case(
        (Place.review_count > 0, Place.rating_sum * 1.0 / Place.review_count),
        else_=0.0,
    )
    if any(term in message for term in ("평점", "별점")):
        statement = statement.order_by(average_rating.desc(), Place.review_count.desc(), Place.id.desc())
    elif any(term in message for term in ("인기", "좋아요")):
        statement = statement.order_by(Place.like_count.desc(), Place.view_count.desc(), Place.id.desc())
    else:
        statement = statement.order_by(Place.like_count.desc(), Place.view_count.desc(), Place.id.desc())

    places = list(session.scalars(statement.limit(limit)).unique())
    if not places and tokens:
        fallback = _place_statement()
        if base_filters:
            fallback = fallback.where(*base_filters)
        places = list(
            session.scalars(
                fallback.order_by(Place.like_count.desc(), Place.view_count.desc(), Place.id.desc()).limit(limit)
            ).unique()
        )
    method: RetrievalMethod = "sqlite_keyword" if category or district or source or tokens else "sqlite_popular"
    return places, method


def _pinecone_retrieve(
    session: Session,
    settings: Settings,
    message: str,
    limit: int = 5,
) -> list[Place]:
    if not settings.chat_semantic_search_enabled or not settings.pinecone_configured:
        return []
    from openai import OpenAI
    from pinecone import Pinecone

    embedding = OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_reason_timeout_seconds,
    ).embeddings.create(model=settings.openai_embedding_model, input=[message]).data[0].embedding
    pinecone = Pinecone(api_key=settings.pinecone_api_key)
    if settings.pinecone_index_name not in {item.name for item in pinecone.list_indexes()}:
        return []
    response = pinecone.Index(settings.pinecone_index_name).query(
        namespace=settings.pinecone_places_namespace,
        vector=embedding,
        top_k=max(limit * 2, 10),
        include_metadata=True,
    )
    place_ids = [int(match.metadata.get("place_id", str(match.id).split(":")[-1])) for match in response.matches]
    if not place_ids:
        return []
    category, district, source = _query_filters(message)
    places_by_id = {
        place.id: place
        for place in session.scalars(_place_statement().where(Place.id.in_(place_ids))).unique()
        if (not category or place.content_type_id == category)
        and (not district or district in place.address)
        and (not source or place.source == source)
    }
    return [places_by_id[place_id] for place_id in place_ids if place_id in places_by_id][:limit]


def retrieve_places(
    session: Session,
    settings: Settings,
    message: str,
) -> tuple[list[Place], RetrievalMethod]:
    try:
        semantic = _pinecone_retrieve(session, settings, message)
    except Exception:
        semantic = []
    if semantic:
        return semantic, "pinecone_semantic"
    return _sqlite_retrieve(session, message)


def _source_payload(place: Place) -> dict[str, object]:
    return {
        "id": place.id,
        "title": place.title,
        "content_type": place.content_type,
        "address": place.address,
        "image_url": image_url(place),
        "source": place.source,
    }


def _grounding_payload(place: Place) -> dict[str, object]:
    return {
        "id": place.id,
        "title": place.title,
        "category": place.content_type,
        "address": place.address,
        "detail_address": place.detail_address,
        "description": place.description,
        "telephone": place.telephone,
        "tags": place_tags(place),
        "source": place.source,
        "likes": place.like_count,
        "views": place.view_count,
        "average_rating": round(place.rating_sum / place.review_count, 1) if place.review_count else 0.0,
        "review_count": place.review_count,
        "schedule": None,
    }


def _rule_answer(places: list[Place]) -> str:
    if not places:
        return "현재 Seoullo 관광 데이터에서 질문과 일치하는 장소를 찾지 못했어요. 지역이나 장소 유형을 조금 더 구체적으로 알려주세요."
    names = ", ".join(place.title for place in places[:3])
    return f"현재 관광 데이터에서 {names}을(를) 찾았어요. 아래 출처 장소를 눌러 주소와 상세 정보를 확인해 보세요."


def generate_grounded_answer(
    settings: Settings,
    message: str,
    history: list[ChatHistoryMessage],
    places: list[Place],
    *,
    client: Any | None = None,
) -> tuple[str, list[int], Literal["openai", "rule"]]:
    if not places or (client is None and not settings.openai_api_key):
        return _rule_answer(places), [place.id for place in places[:3]], "rule"
    try:
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_reason_timeout_seconds)
        expected_ids = {place.id for place in places}
        response = client.responses.parse(
            model=settings.openai_chat_model,
            reasoning={"effort": "minimal"},
            max_output_tokens=2000,
            store=False,
            input=[
                {
                    "role": "system",
                    "content": (
                        "당신은 Seoullo의 서울 여행 안내 챗봇입니다. 제공된 retrieved_places만 근거로 한국어로 답하세요. "
                        "장소명, 주소, 카테고리처럼 입력에 있는 사실만 사용하고 없는 운영시간, 가격, 축제 날짜, 일정은 만들지 마세요. "
                        "일정 필드가 null이면 데이터에 일정 정보가 없다고 분명히 안내하세요. 질문에 맞는 근거가 부족하면 솔직히 부족하다고 말하세요. "
                        "답변은 모바일에서 읽기 쉽게 4문장 이내로 작성하고 언급한 장소 ID만 cited_place_ids에 넣으세요."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": message,
                            "recent_history": [item.model_dump() for item in history[-6:]],
                            "retrieved_places": [_grounding_payload(place) for place in places],
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                },
            ],
            text_format=GeneratedChatAnswer,
        )
        parsed = response.output_parsed
        if parsed is None or any(place_id not in expected_ids for place_id in parsed.cited_place_ids):
            raise ValueError("Chat response citations did not match retrieved places")
        cited = parsed.cited_place_ids or [place.id for place in places[:3]]
        return parsed.answer, cited, "openai"
    except Exception:
        return _rule_answer(places), [place.id for place in places[:3]], "rule"


def chat_response(
    session: Session,
    settings: Settings,
    message: str,
    history: list[ChatHistoryMessage],
) -> dict[str, object]:
    places, method = retrieve_places(session, settings, message.strip())
    answer, cited_ids, answer_source = generate_grounded_answer(
        settings,
        message.strip(),
        history,
        places,
    )
    cited_set = set(cited_ids)
    sources = [_source_payload(place) for place in places if place.id in cited_set]
    return {
        "answer": answer,
        "retrieval_method": method,
        "answer_source": answer_source,
        "sources": sources,
    }
