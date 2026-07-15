from math import isclose, sqrt

import pytest

from app.core.emotions import (
    EMOTION_COLUMNS,
    EMOTION_VECTOR_DIMENSION,
    EmotionValidationError,
    emotion_vector,
    validate_emotion_payload,
)


SAMPLE = {
    "mood": {"지침": 4, "불안": 2, "답답함": 4, "설렘": 2, "외로움": 2, "평온함": 5},
    "afterFeeling": {"회복": 5, "해방": 3, "활력": 2, "위로": 2, "몰입": 1, "설렘": 2},
    "style": {"조용히 혼자": 4, "가볍게 산책": 5, "새로운 자극": 2, "누군가와 함께": 4},
}


def test_fixed_emotion_schema_and_weighted_vector() -> None:
    values = validate_emotion_payload(SAMPLE)
    vector = emotion_vector(values)

    assert tuple(values) == EMOTION_COLUMNS
    assert len(vector) == EMOTION_VECTOR_DIMENSION == 16
    assert isclose(sqrt(sum(value * value for value in vector)), 1.0, rel_tol=1e-9)
    assert isclose(sum(value * value for value in vector[:6]), 0.40, rel_tol=1e-9)
    assert isclose(sum(value * value for value in vector[6:12]), 0.35, rel_tol=1e-9)
    assert isclose(sum(value * value for value in vector[12:]), 0.25, rel_tol=1e-9)


def test_emotion_schema_rejects_missing_or_out_of_range_values() -> None:
    missing = {**SAMPLE, "style": {"조용히 혼자": 4}}
    with pytest.raises(EmotionValidationError):
        validate_emotion_payload(missing)

    invalid = {
        **SAMPLE,
        "mood": {**SAMPLE["mood"], "지침": 6},
    }
    with pytest.raises(EmotionValidationError):
        validate_emotion_payload(invalid)
