from __future__ import annotations

import json
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import Settings


logger = logging.getLogger(__name__)


class GeneratedRecommendationReason(BaseModel):
    place_id: int
    reason: str = Field(min_length=10, max_length=180)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return " ".join(value.split())


class GeneratedRecommendationReasons(BaseModel):
    reasons: list[GeneratedRecommendationReason] = Field(min_length=5, max_length=5)


ReasonSource = Literal["openai", "rule"]


def _joined(values: list[str]) -> str:
    return "·".join(values)


def rule_based_reason(
    selections: dict[str, list[str]],
    matched_keywords: list[dict[str, object]],
) -> str:
    mood = _joined(selections["mood"])
    after = _joined(selections["afterFeeling"])
    style = _joined(selections["style"])
    strongest = sorted(
        matched_keywords,
        key=lambda match: (-int(match["value"]), str(match["keyword"])),
    )[:2]
    evidence = ", ".join(
        f"{match['keyword']} {match['value']}점" for match in strongest
    )
    return (
        f"{mood} 상태에서 {style} 방식으로 머물며 {after} 감정을 기대하기 좋은 장소예요. "
        f"감정 데이터에서도 {evidence} 항목이 높게 나타났어요."
    )


def _fallback_reasons(
    selections: dict[str, list[str]],
    items: list[dict[str, object]],
) -> dict[int, tuple[str, ReasonSource]]:
    return {
        int(item["place"]["id"]): (
            rule_based_reason(selections, item["matched_keywords"]),
            "rule",
        )
        for item in items
    }


def _prompt_payload(
    selections: dict[str, list[str]],
    items: list[dict[str, object]],
) -> str:
    places = []
    for item in items:
        place = item["place"]
        places.append(
            {
                "place_id": place["id"],
                "title": place["title"],
                "category": place["content_type"],
                "address": place["address"],
                "similarity": item["similarity"],
                "matched_keywords": item["matched_keywords"],
            }
        )
    return json.dumps(
        {"selected_emotions": selections, "ranked_places": places},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def generate_recommendation_reasons(
    settings: Settings,
    selections: dict[str, list[str]],
    items: list[dict[str, object]],
    *,
    client: Any | None = None,
) -> dict[int, tuple[str, ReasonSource]]:
    fallback = _fallback_reasons(selections, items)
    if len(items) != 5 or (client is None and not settings.openai_api_key):
        return fallback

    try:
        if client is None:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_reason_timeout_seconds,
            )
        response = client.responses.parse(
            model=settings.openai_chat_model,
            max_output_tokens=2000,
            reasoning={"effort": "minimal"},
            store=False,
            input=[
                {
                    "role": "system",
                    "content": (
                        "당신은 서울 장소 추천 결과를 설명하는 한국어 카피라이터입니다. "
                        "장소 순위, 유사도, place_id는 이미 16차원 감정 벡터 알고리즘으로 확정됐습니다. "
                        "절대 순위를 다시 판단하거나 바꾸지 말고 입력된 5개 장소 각각의 이유만 작성하세요. "
                        "입력에 없는 사실은 만들지 말고 선택 감정과 matched_keywords 수치를 근거로 "
                        "각 이유를 자연스러운 한국어 1~2문장, 120자 이내로 작성하세요."
                    ),
                },
                {
                    "role": "user",
                    "content": _prompt_payload(selections, items),
                },
            ],
            text_format=GeneratedRecommendationReasons,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("OpenAI structured response was empty")

        expected_ids = [int(item["place"]["id"]) for item in items]
        generated_ids = [reason.place_id for reason in parsed.reasons]
        if len(set(generated_ids)) != 5 or set(generated_ids) != set(expected_ids):
            raise ValueError("OpenAI response place IDs did not match the ranked places")

        generated = {reason.place_id: reason.reason for reason in parsed.reasons}
        return {place_id: (generated[place_id], "openai") for place_id in expected_ids}
    except Exception as exc:
        logger.warning("Recommendation reason generation fell back to rules: %s", type(exc).__name__)
        return fallback
