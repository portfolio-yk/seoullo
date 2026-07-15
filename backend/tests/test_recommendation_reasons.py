from types import SimpleNamespace

from app.core.config import Settings
from app.services.recommendation_reasons import (
    GeneratedRecommendationReason,
    GeneratedRecommendationReasons,
    generate_recommendation_reasons,
)


def _items() -> list[dict[str, object]]:
    return [
        {
            "rank": index,
            "similarity": 1 - index / 100,
            "matched_keywords": [
                {"group": "mood", "keyword": "지침", "value": 5},
                {"group": "afterFeeling", "keyword": "회복", "value": 4},
            ],
            "place": {
                "id": index,
                "title": f"장소 {index}",
                "content_type": "관광지",
                "address": "서울특별시",
            },
        }
        for index in range(1, 6)
    ]


def _selections() -> dict[str, list[str]]:
    return {
        "mood": ["지침"],
        "afterFeeling": ["회복"],
        "style": ["가볍게 산책"],
    }


class FakeResponses:
    def __init__(self, parsed: GeneratedRecommendationReasons | None = None, error: Exception | None = None):
        self.parsed = parsed
        self.error = error
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(output_parsed=self.parsed)


def test_openai_generates_all_five_reasons_in_one_call() -> None:
    parsed = GeneratedRecommendationReasons(
        reasons=[
            GeneratedRecommendationReason(
                place_id=index,
                reason=f"장소 {index}는 선택한 감정 흐름과 잘 맞는 장소입니다.",
            )
            for index in reversed(range(1, 6))
        ]
    )
    responses = FakeResponses(parsed=parsed)
    client = SimpleNamespace(responses=responses)

    result = generate_recommendation_reasons(
        Settings(_env_file=None, openai_api_key="test-key"),
        _selections(),
        _items(),
        client=client,
    )

    assert len(responses.calls) == 1
    assert list(result) == [1, 2, 3, 4, 5]
    assert {source for _, source in result.values()} == {"openai"}
    assert responses.calls[0]["text_format"] is GeneratedRecommendationReasons


def test_openai_failure_uses_rule_reasons_without_losing_results() -> None:
    responses = FakeResponses(error=RuntimeError("temporary failure"))
    client = SimpleNamespace(responses=responses)

    result = generate_recommendation_reasons(
        Settings(_env_file=None, openai_api_key="test-key"),
        _selections(),
        _items(),
        client=client,
    )

    assert len(responses.calls) == 1
    assert list(result) == [1, 2, 3, 4, 5]
    assert {source for _, source in result.values()} == {"rule"}
    assert all(reason for reason, _ in result.values())


def test_missing_openai_key_skips_network_call() -> None:
    result = generate_recommendation_reasons(
        Settings(_env_file=None, openai_api_key=""),
        _selections(),
        _items(),
    )

    assert {source for _, source in result.values()} == {"rule"}
