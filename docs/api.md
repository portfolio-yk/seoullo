# Seoullo API 명세

기본 경로는 `/api`이며 개발 서버의 전체 대화형 명세는 `/docs`에서 확인할 수 있습니다.

## 공통 정책

- 장소·리뷰 수정과 삭제는 생성 시 입력한 비밀번호가 필요합니다.
- 데이터셋 장소는 수정·삭제할 수 없습니다.
- 태그는 장소당 최대 10개, 태그당 6자 이하입니다.
- 업로드 이미지는 파일당 5MB 이하입니다.
- 리뷰는 장소별 익명 식별값당 1개만 작성할 수 있습니다.
- 좋아요는 같은 익명 식별값의 재요청 시 해제되는 토글 방식입니다.

## 시스템과 지도

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/health` | 서버와 DB 상태 확인 |
| GET | `/api/maps/address-search?q=` | Kakao 주소·장소 검색 |
| GET | `/api/maps/reverse-geocode?latitude=&longitude=` | 좌표의 주소 조회 |

## 장소

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/places` | 검색·필터·정렬·페이지 목록 |
| GET | `/api/places/categories` | 카테고리별 장소 수 |
| GET | `/api/places/map-points` | 지도용 장소 좌표 |
| GET | `/api/places/duplicate-check` | 제목·좌표 중복 후보 확인 |
| GET | `/api/places/{place_id}` | 장소 상세 |
| POST | `/api/places` | 사용자 장소 등록 |
| PUT | `/api/places/{place_id}` | 사용자 장소 수정 |
| DELETE | `/api/places/{place_id}` | 사용자 장소 삭제 |
| GET | `/api/places/{place_id}/images/{image_id}` | 업로드 이미지 조회 |
| DELETE | `/api/places/{place_id}/images/{image_id}` | 사용자 장소 이미지 삭제 |

목록은 `q`, `content_type_id`, `source`, `ids`, `sort`, `latitude`, `longitude`, `radius_meters`, `page`, `size`를 지원합니다. `sort`는 `latest`, `rating`, `likes`, `distance` 중 하나입니다.

장소 등록·수정은 `multipart/form-data`를 사용합니다. 등록 필수값은 `title`, `content_type_id`, `description`, `latitude`, `longitude`, `password`이며 `tags`, 주소·상세 주소·이미지는 선택입니다. 태그를 전달하면 개수·글자 수 제한을 검증합니다. 중복 경고를 확인한 뒤 등록할 때는 `allow_duplicate=true`를 함께 전달합니다.

## 태그

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/tags/popular` | 사용량 기준 인기 태그 |
| POST | `/api/places/{place_id}/tags` | 장소에 태그 추가 |
| DELETE | `/api/places/{place_id}/tags/{tag_name}` | 사용자 장소의 태그 삭제 |

태그 추가 요청 예시는 다음과 같습니다.

```json
{
  "tags": ["산책", "야경"]
}
```

태그 추가에는 비밀번호가 필요하지 않습니다. 데이터셋 장소의 태그는 삭제할 수 없고, 사용자 장소의 태그 삭제에는 장소 비밀번호가 필요합니다. 변경 결과는 lexical 인덱스에 반영됩니다.

## 리뷰와 상호작용

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/places/{place_id}/reviews` | 장소 리뷰 목록 |
| POST | `/api/places/{place_id}/reviews` | 별점 1~5와 리뷰 작성 |
| PUT | `/api/reviews/{review_id}` | 리뷰 수정 |
| DELETE | `/api/reviews/{review_id}` | 리뷰 삭제 |
| POST | `/api/places/{place_id}/like` | 장소 좋아요 토글 |
| POST | `/api/reviews/{review_id}/like` | 리뷰 좋아요 토글 |
| POST | `/api/places/{place_id}/view` | 장소 조회수 증가 |

프론트엔드는 열람한 장소 ID를 로컬 스토리지에 보관해 같은 브라우저에서 중복 조회 요청을 보내지 않습니다.

## 감정 추천과 체크인

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/emotions/recommendations` | 16차원 감정 유사도 상위 5곳 추천 |
| POST | `/api/emotions/checkins` | 방문 후 감정 체크인 및 프로필 갱신 |

추천 요청:

```json
{
  "mood": ["지침", "답답함"],
  "afterFeeling": ["회복", "해방"],
  "style": ["가볍게 산책"],
  "latitude": 37.5665,
  "longitude": 126.978
}
```

`mood`와 `afterFeeling`은 하나 이상, `style`은 정확히 하나를 전달합니다. 위치는 선택이며 위도와 경도를 함께 보내야 합니다.

체크인 요청:

```json
{
  "place_id": 1,
  "before_emotion": "지침",
  "before_intensity": 4,
  "after_emotion": "회복",
  "after_intensity": 3,
  "travel_style": "가볍게 산책"
}
```

## 챗봇

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/chat/messages` | 관광 장소 검색과 답변 생성 |

```json
{
  "message": "답답할 때 산책하기 좋은 곳 찾아줘",
  "history": [
    {"role": "user", "content": "종로구 위주로 알려줘"}
  ]
}
```

`history`는 최대 10개, 메시지는 최대 500자입니다. 응답은 사용자용 답변, 의도, 최대 3개의 장소 카드, 내부 검색 상태를 포함합니다. 화면에는 사용자에게 필요한 답변과 장소 정보만 표시합니다.
