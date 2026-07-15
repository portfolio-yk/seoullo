from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from collections.abc import Collection
from typing import Any, Mapping


@dataclass(frozen=True)
class EmotionField:
    group: str
    keyword: str
    column: str


EMOTION_FIELDS: tuple[EmotionField, ...] = (
    EmotionField("mood", "지침", "mood_fatigue"),
    EmotionField("mood", "불안", "mood_anxiety"),
    EmotionField("mood", "답답함", "mood_stifled"),
    EmotionField("mood", "설렘", "mood_excitement"),
    EmotionField("mood", "외로움", "mood_loneliness"),
    EmotionField("mood", "평온함", "mood_calm"),
    EmotionField("afterFeeling", "회복", "after_recovery"),
    EmotionField("afterFeeling", "해방", "after_release"),
    EmotionField("afterFeeling", "활력", "after_vitality"),
    EmotionField("afterFeeling", "위로", "after_comfort"),
    EmotionField("afterFeeling", "몰입", "after_immersion"),
    EmotionField("afterFeeling", "설렘", "after_excitement"),
    EmotionField("style", "조용히 혼자", "style_quiet_solo"),
    EmotionField("style", "가볍게 산책", "style_light_walk"),
    EmotionField("style", "새로운 자극", "style_new_stimulation"),
    EmotionField("style", "누군가와 함께", "style_together"),
)

EMOTION_VECTOR_DIMENSION = len(EMOTION_FIELDS)
EMOTION_GROUP_WEIGHTS = {"mood": 0.40, "afterFeeling": 0.35, "style": 0.25}
EMOTION_COLUMNS = tuple(field.column for field in EMOTION_FIELDS)
EMOTION_COLUMN_BY_KEYWORD = {
    (field.group, field.keyword): field.column for field in EMOTION_FIELDS
}


class EmotionValidationError(ValueError):
    pass


def validate_emotion_payload(payload: Any) -> dict[str, int]:
    if not isinstance(payload, Mapping):
        raise EmotionValidationError("emotion은 객체여야 합니다.")

    expected_groups = set(EMOTION_GROUP_WEIGHTS)
    actual_groups = set(payload)
    if actual_groups != expected_groups:
        raise EmotionValidationError(
            f"emotion 그룹은 {sorted(expected_groups)}와 정확히 일치해야 합니다."
        )

    values: dict[str, int] = {}
    for group in EMOTION_GROUP_WEIGHTS:
        group_payload = payload[group]
        if not isinstance(group_payload, Mapping):
            raise EmotionValidationError(f"emotion.{group}은 객체여야 합니다.")
        fields = [field for field in EMOTION_FIELDS if field.group == group]
        expected_keywords = {field.keyword for field in fields}
        if set(group_payload) != expected_keywords:
            raise EmotionValidationError(
                f"emotion.{group} 키는 {sorted(expected_keywords)}와 정확히 일치해야 합니다."
            )
        for field in fields:
            value = group_payload[field.keyword]
            if isinstance(value, bool) or not isinstance(value, int):
                raise EmotionValidationError(
                    f"emotion.{group}.{field.keyword} 값은 정수여야 합니다."
                )
            if not 0 <= value <= 5:
                raise EmotionValidationError(
                    f"emotion.{group}.{field.keyword} 초기값은 0~5여야 합니다."
                )
            values[field.column] = value
    return values


def emotion_vector(values: Mapping[str, int | float]) -> list[float]:
    """Return a group-normalized, weighted vector in the fixed 16-field order."""
    vector: list[float] = []
    for group, weight in EMOTION_GROUP_WEIGHTS.items():
        fields = [field for field in EMOTION_FIELDS if field.group == group]
        raw = [float(values.get(field.column, 0)) for field in fields]
        norm = sqrt(sum(value * value for value in raw))
        multiplier = sqrt(weight)
        vector.extend((value / norm) * multiplier if norm else 0.0 for value in raw)
    return vector


def selection_values(selections: Mapping[str, Collection[str]]) -> dict[str, int]:
    values = {column: 0 for column in EMOTION_COLUMNS}
    for field in EMOTION_FIELDS:
        if field.keyword in selections.get(field.group, ()):
            values[field.column] = 1
    return values


def emotion_payload(values: Mapping[str, int | float]) -> dict[str, dict[str, int]]:
    """Return the fixed dataset-compatible nested emotion shape."""
    return {
        group: {
            field.keyword: int(values.get(field.column, 0))
            for field in EMOTION_FIELDS
            if field.group == group
        }
        for group in EMOTION_GROUP_WEIGHTS
    }
