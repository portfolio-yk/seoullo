from __future__ import annotations

from collections import Counter
import hashlib
from math import log1p, sqrt
import re
import unicodedata

from app.db.models import Place


MAX_SPARSE_VALUES = 900
FIELD_WEIGHTS = {
    "title": 5.0,
    "content_type": 4.0,
    "tags": 3.0,
    "address": 2.0,
    "description": 1.0,
}

SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("공원", "한강공원", "생태공원", "근린공원", "수목원", "정원"),
    ("궁궐", "고궁", "왕궁", "유적지", "문화유산"),
    ("사찰", "템플스테이"),
    ("박물관", "전시관"),
    ("미술관", "갤러리"),
    ("공연장", "극장", "영화관"),
    ("캠핑장", "야영장"),
    ("수영장", "워터파크"),
    ("호텔", "숙소", "숙박", "게스트하우스", "모텔", "리조트", "한옥스테이"),
    ("시장", "전통시장", "야시장"),
    ("백화점", "쇼핑몰", "아울렛", "면세점"),
)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[가-힣a-z0-9]+", normalized))


def _features(value: str) -> Counter[str]:
    normalized = _normalize(value)
    features: Counter[str] = Counter()
    if not normalized:
        return features
    compact = normalized.replace(" ", "")
    if 2 <= len(compact) <= 80:
        features[compact] += 1.25
    for word in normalized.split():
        if len(word) < 2:
            continue
        features[word] += 1.0
        for width, weight in ((2, 0.55), (3, 0.7)):
            if len(word) <= width:
                continue
            for offset in range(len(word) - width + 1):
                features[word[offset : offset + width]] += weight
    for group in SYNONYM_GROUPS:
        if any(term in normalized for term in group):
            for term in group:
                features[term] += 0.35
    return features


def _token_index(token: str) -> int:
    digest = hashlib.blake2s(
        token.encode("utf-8"),
        digest_size=4,
        person=b"seoullo",
    ).digest()
    return int.from_bytes(digest, "big", signed=False)


def sparse_vector(weighted_texts: list[tuple[str, float]]) -> dict[str, list[int] | list[float]]:
    token_weights: Counter[str] = Counter()
    for text, field_weight in weighted_texts:
        for token, frequency in _features(text).items():
            token_weights[token] += field_weight * (1.0 + log1p(frequency))

    strongest = token_weights.most_common(MAX_SPARSE_VALUES)
    hashed_weights: Counter[int] = Counter()
    for token, weight in strongest:
        hashed_weights[_token_index(token)] += weight
    strongest_hashed = hashed_weights.most_common(MAX_SPARSE_VALUES)
    norm = sqrt(sum(weight * weight for _index, weight in strongest_hashed))
    if not norm:
        return {"indices": [], "values": []}
    ordered = sorted((index, weight / norm) for index, weight in strongest_hashed)
    return {
        "indices": [index for index, _weight in ordered],
        "values": [round(weight, 8) for _index, weight in ordered],
    }


def place_sparse_vector(place: Place) -> dict[str, list[int] | list[float]]:
    tags = " ".join(association.tag.name for association in place.place_tags)
    return sparse_vector(
        [
            (place.title or "", FIELD_WEIGHTS["title"]),
            (place.content_type or "", FIELD_WEIGHTS["content_type"]),
            (tags, FIELD_WEIGHTS["tags"]),
            (
                " ".join(part for part in (place.address, place.detail_address) if part),
                FIELD_WEIGHTS["address"],
            ),
            ((place.description or "")[:2000], FIELD_WEIGHTS["description"]),
        ]
    )


def query_sparse_vector(
    terms: list[str],
    *,
    category: str | None = None,
    district: str | None = None,
) -> dict[str, list[int] | list[float]]:
    return sparse_vector(
        [
            (" ".join(dict.fromkeys(terms)), FIELD_WEIGHTS["title"]),
            (category or "", FIELD_WEIGHTS["content_type"]),
            (district or "", FIELD_WEIGHTS["address"]),
        ]
    )


def place_lexical_record(place: Place) -> dict[str, object]:
    tags = [association.tag.name for association in place.place_tags]
    return {
        "id": f"place:{place.id}",
        "sparse_values": place_sparse_vector(place),
        "metadata": {
            "place_id": place.id,
            "content_id": place.content_id or "",
            "source": place.source,
            "title": place.title,
            "content_type_id": place.content_type_id,
            "content_type": place.content_type,
            "region": place.region,
            "address": place.address,
            "tags": tags,
        },
    }
