# 감정 기반 추천 API

## Endpoint

`POST /api/emotions/recommendations`

AI 모델을 사용하지 않고 고정 16차원 감정 벡터의 cosine 유사도로 장소 5곳을 반환합니다.

## 요청

```json
{
  "mood": ["지침", "답답함"],
  "afterFeeling": ["회복", "해방"],
  "style": ["가볍게 산책"]
}
```

각 그룹은 하나 이상의 키워드가 필요하며 중복 키워드는 허용하지 않습니다. 선택적으로 `latitude`, `longitude`를 함께 전달하면 결과 장소의 거리를 계산합니다.

## 응답

```json
{
  "algorithm": "pinecone_cosine",
  "vector_dimension": 16,
  "weights": {
    "mood": 0.4,
    "afterFeeling": 0.35,
    "style": 0.25
  },
  "items": [
    {
      "rank": 1,
      "similarity": 0.91,
      "matched_keywords": [
        { "group": "mood", "keyword": "지침", "value": 5 }
      ],
      "place": { "id": 1, "title": "장소명" }
    }
  ]
}
```

## 장애 대체

Pinecone 연결 실패, 설정 누락 또는 결과 부족 시 SQLite의 6,518개 감정 프로필에 같은 정규화와 cosine 계산을 적용합니다. 이 경우 `algorithm`은 `sqlite_cosine_fallback`입니다. 두 방식 모두 AI 모델은 사용하지 않습니다.

추천 이유 생성은 순위를 확정한 뒤 처리하며, 자세한 내용은 `emotion-recommendation-reasons.md`를 참고합니다.
