from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
import logging
from typing import Any

from sqlalchemy import select

from app.core.config import Settings
from app.core.emotions import EMOTION_COLUMNS, EMOTION_VECTOR_DIMENSION, emotion_vector
from app.db.models import Place, PlaceEmotionProfile
from app.db.session import SessionLocal


EMBEDDING_DIMENSION = 1536
logger = logging.getLogger(__name__)


@dataclass
class EmotionIndexReport:
    index_name: str
    namespace: str
    dimension: int
    upserted: int
    skipped_zero_vectors: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _place_text(place: Place) -> str:
    fields = [
        f"장소명: {place.title}",
        f"유형: {place.content_type}",
        f"주소: {place.address} {place.detail_address}".strip(),
        f"설명: {place.description}" if place.description else "",
        f"좌표: {place.latitude}, {place.longitude}",
    ]
    return "\n".join(field for field in fields if field)


def _place_vector_record(place: Place, embedding: list[float]) -> dict[str, object]:
    return {
        "id": f"place:{place.id}",
        "values": embedding,
        "metadata": {
            "place_id": place.id,
            "content_id": place.content_id or "",
            "source": place.source,
            "title": place.title,
            "content_type": place.content_type,
            "region": place.region,
        },
    }


def _chunks(values: list[Any], size: int) -> Iterable[list[Any]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _ensure_index(pinecone, *, name: str, dimension: int, settings: Settings):
    from pinecone import ServerlessSpec

    index_names = {item.name for item in pinecone.list_indexes()}
    if name not in index_names:
        pinecone.create_index(
            name=name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )
    else:
        description = pinecone.describe_index(name)
        if int(description.dimension) != dimension:
            raise RuntimeError(
                f"Pinecone 인덱스 {name}의 차원은 {description.dimension}이며 필요한 차원은 {dimension}입니다."
            )
    return pinecone.Index(name)


def rebuild_places_namespace(settings: Settings) -> int:
    if not settings.pinecone_configured:
        raise RuntimeError("OPENAI_API_KEY와 PINECONE_API_KEY가 필요합니다.")

    from openai import OpenAI
    from pinecone import Pinecone

    openai_client = OpenAI(api_key=settings.openai_api_key)
    pinecone = Pinecone(api_key=settings.pinecone_api_key)
    index = _ensure_index(
        pinecone,
        name=settings.pinecone_index_name,
        dimension=EMBEDDING_DIMENSION,
        settings=settings,
    )

    for namespace in (
        settings.pinecone_places_namespace,
        settings.pinecone_checkins_namespace,
        settings.pinecone_community_namespace,
    ):
        try:
            index.delete(delete_all=True, namespace=namespace)
        except Exception:
            pass

    with SessionLocal() as session:
        places = list(session.scalars(select(Place).order_by(Place.id)))

    upserted = 0
    for batch in _chunks(places, 100):
        response = openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=[_place_text(place) for place in batch],
        )
        vectors = [
            _place_vector_record(place, embedding.embedding)
            for place, embedding in zip(batch, response.data, strict=True)
        ]
        index.upsert(vectors=vectors, namespace=settings.pinecone_places_namespace)
        upserted += len(vectors)
    return upserted


def _profile_values(profile: PlaceEmotionProfile) -> dict[str, int]:
    return {column: int(getattr(profile, column)) for column in EMOTION_COLUMNS}


def _emotion_vector_record(place: Place, profile: PlaceEmotionProfile) -> dict[str, object] | None:
    values = _profile_values(profile)
    if not any(values.values()):
        return None
    return {
        "id": f"emotion:{place.id}",
        "values": emotion_vector(values),
        "metadata": {
            "place_id": place.id,
            "content_id": place.content_id or "",
            "source": place.source,
            "title": place.title,
            "content_type_id": place.content_type_id,
            "content_type": place.content_type,
            "region": place.region,
            "emotion_total": sum(values.values()),
        },
    }


def rebuild_emotion_index(settings: Settings) -> EmotionIndexReport:
    if not settings.pinecone_emotion_configured:
        raise RuntimeError("PINECONE_API_KEY가 필요합니다.")

    from pinecone import Pinecone

    pinecone = Pinecone(api_key=settings.pinecone_api_key)
    index = _ensure_index(
        pinecone,
        name=settings.pinecone_emotion_index_name,
        dimension=EMOTION_VECTOR_DIMENSION,
        settings=settings,
    )
    try:
        index.delete(delete_all=True, namespace=settings.pinecone_emotion_namespace)
    except Exception:
        pass

    with SessionLocal() as session:
        rows = list(
            session.execute(
                select(Place, PlaceEmotionProfile)
                .join(PlaceEmotionProfile, PlaceEmotionProfile.place_id == Place.id)
                .order_by(Place.id)
            ).all()
        )

    vectors: list[dict[str, object]] = []
    skipped_zero = 0
    for place, profile in rows:
        record = _emotion_vector_record(place, profile)
        if record is None:
            skipped_zero += 1
        else:
            vectors.append(record)

    for batch in _chunks(vectors, 100):
        index.upsert(vectors=batch, namespace=settings.pinecone_emotion_namespace)

    return EmotionIndexReport(
        index_name=settings.pinecone_emotion_index_name,
        namespace=settings.pinecone_emotion_namespace,
        dimension=EMOTION_VECTOR_DIMENSION,
        upserted=len(vectors),
        skipped_zero_vectors=skipped_zero,
    )


def upsert_emotion_place(settings: Settings, place_id: int) -> bool:
    """Refresh one place after a check-in. Returns False for a zero-vector profile."""
    if not settings.pinecone_emotion_configured:
        raise RuntimeError("PINECONE_API_KEY가 필요합니다.")

    from pinecone import Pinecone

    with SessionLocal() as session:
        row = session.execute(
            select(Place, PlaceEmotionProfile)
            .join(PlaceEmotionProfile, PlaceEmotionProfile.place_id == Place.id)
            .where(Place.id == place_id)
        ).one_or_none()
    if row is None:
        raise RuntimeError(f"감정 프로필이 없는 장소입니다: {place_id}")

    pinecone = Pinecone(api_key=settings.pinecone_api_key)
    index = _ensure_index(
        pinecone,
        name=settings.pinecone_emotion_index_name,
        dimension=EMOTION_VECTOR_DIMENSION,
        settings=settings,
    )
    record = _emotion_vector_record(*row)
    vector_id = f"emotion:{place_id}"
    if record is None:
        index.delete(ids=[vector_id], namespace=settings.pinecone_emotion_namespace)
        return False
    index.upsert(vectors=[record], namespace=settings.pinecone_emotion_namespace)
    return True


def upsert_emotion_record(
    settings: Settings,
    place: Place,
    profile: PlaceEmotionProfile,
) -> bool:
    """Upsert the current in-memory profile, including uncommitted check-in increments."""
    if not settings.pinecone_emotion_configured:
        raise RuntimeError("PINECONE_API_KEY가 필요합니다.")
    from pinecone import Pinecone

    pinecone = Pinecone(api_key=settings.pinecone_api_key)
    index = _ensure_index(
        pinecone,
        name=settings.pinecone_emotion_index_name,
        dimension=EMOTION_VECTOR_DIMENSION,
        settings=settings,
    )
    record = _emotion_vector_record(place, profile)
    vector_id = f"emotion:{place.id}"
    if record is None:
        index.delete(ids=[vector_id], namespace=settings.pinecone_emotion_namespace)
        return False
    index.upsert(vectors=[record], namespace=settings.pinecone_emotion_namespace)
    return True


def sync_place_vectors(
    settings: Settings,
    place: Place,
    profile: PlaceEmotionProfile,
) -> bool:
    """Always sync emotion vector; return whether semantic RAG embedding also synced."""
    if not settings.pinecone_emotion_configured:
        raise RuntimeError("PINECONE_API_KEY가 필요합니다.")
    from openai import OpenAI, PermissionDeniedError
    from pinecone import Pinecone

    pinecone = Pinecone(api_key=settings.pinecone_api_key)
    emotions_index = _ensure_index(
        pinecone,
        name=settings.pinecone_emotion_index_name,
        dimension=EMOTION_VECTOR_DIMENSION,
        settings=settings,
    )
    emotion_record = _emotion_vector_record(place, profile)
    if emotion_record is None:
        raise RuntimeError("장소 감정 프로필이 비어 있습니다.")
    emotions_index.upsert(
        vectors=[emotion_record],
        namespace=settings.pinecone_emotion_namespace,
    )

    if not settings.openai_api_key:
        return False
    try:
        openai_client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_reason_timeout_seconds,
        )
        embedding = openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=[_place_text(place)],
        ).data[0].embedding
    except PermissionDeniedError:
        logger.warning("Semantic place embedding skipped: model permission denied")
        return False

    places_index = _ensure_index(
        pinecone,
        name=settings.pinecone_index_name,
        dimension=EMBEDDING_DIMENSION,
        settings=settings,
    )
    places_index.upsert(
        vectors=[_place_vector_record(place, embedding)],
        namespace=settings.pinecone_places_namespace,
    )
    return True


def delete_place_vectors(settings: Settings, place_id: int) -> None:
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY가 필요합니다.")
    from pinecone import Pinecone

    pinecone = Pinecone(api_key=settings.pinecone_api_key)
    index_names = {item.name for item in pinecone.list_indexes()}
    if settings.pinecone_index_name in index_names:
        pinecone.Index(settings.pinecone_index_name).delete(
            ids=[f"place:{place_id}"],
            namespace=settings.pinecone_places_namespace,
        )
    if settings.pinecone_emotion_index_name in index_names:
        pinecone.Index(settings.pinecone_emotion_index_name).delete(
            ids=[f"emotion:{place_id}"],
            namespace=settings.pinecone_emotion_namespace,
        )
