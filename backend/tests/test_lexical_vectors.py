from app.db.models import Place, PlaceTag, Tag
from app.services.lexical_vectors import (
    MAX_SPARSE_VALUES,
    place_lexical_record,
    query_sparse_vector,
    sparse_vector,
)


def _dot(left: dict[str, list], right: dict[str, list]) -> float:
    left_values = dict(zip(left["indices"], left["values"], strict=True))
    return sum(
        left_values.get(index, 0.0) * value
        for index, value in zip(right["indices"], right["values"], strict=True)
    )


def test_sparse_vectors_are_deterministic_sorted_and_bounded() -> None:
    weighted = [("양화한강공원 산책 휴식 " * 500, 5.0)]
    first = sparse_vector(weighted)
    second = sparse_vector(weighted)

    assert first == second
    assert first["indices"] == sorted(first["indices"])
    assert len(first["indices"]) <= MAX_SPARSE_VALUES
    assert len(first["indices"]) == len(first["values"])


def test_title_and_category_sparse_features_rank_matching_place_higher() -> None:
    query = query_sparse_vector(["공원"], category="관광지")
    park = sparse_vector([("양화한강공원", 5.0), ("관광지", 4.0)])
    hotel = sparse_vector([("도심 비즈니스 호텔", 5.0), ("숙박", 4.0)])

    assert _dot(query, park) > _dot(query, hotel)
    assert _dot(query, park) > 0


def test_place_record_contains_sparse_vector_and_filter_metadata() -> None:
    place = Place(
        id=10,
        content_id="public-10",
        source="dataset",
        region="서울",
        content_type="관광지",
        content_type_id="12",
        title="양화한강공원",
        description="산책하기 좋은 한강공원",
        address="서울특별시 영등포구",
        longitude=126.9,
        latitude=37.5,
    )
    place.place_tags.append(
        PlaceTag(tag=Tag(name="산책", normalized_name="산책", usage_count=1))
    )

    record = place_lexical_record(place)

    assert record["id"] == "place:10"
    assert record["sparse_values"]["indices"]
    assert record["metadata"]["content_type_id"] == "12"
    assert record["metadata"]["tags"] == ["산책"]
