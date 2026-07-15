# 장소 API

기본 경로는 `/api/places`입니다. Swagger UI는 백엔드 실행 후 `/docs`에서 확인할 수 있습니다.

## 조회

### `GET /api/places`

| 파라미터 | 설명 |
|---|---|
| `q` | 장소명·설명·주소 검색. `#태그` 형식은 정확한 태그 검색 |
| `content_type_id` | 관광 유형 ID |
| `source` | `dataset` 또는 `user` |
| `sort` | `latest`, `rating`, `likes`, `distance` |
| `latitude`, `longitude` | 거리 표시·거리순 정렬 기준 좌표 |
| `page`, `size` | 페이지와 페이지 크기(최대 100) |

`distance` 정렬에는 위도와 경도가 모두 필요합니다. 추천순은 제공하지 않으며 좋아요순을 사용합니다.

### 기타 조회

- `GET /api/places/categories`: 카테고리별 장소 수
- `GET /api/places/duplicate-check`: 같은 이름·50m 이내 중복 후보
- `GET /api/places/{id}`: 장소 상세
- `GET /api/places/{placeId}/images/{imageId}`: SQLite BLOB 이미지

## 사용자 장소 생성

`POST /api/places`는 `multipart/form-data`를 사용합니다.

필수 필드:

- `title`
- `content_type_id`
- `description`
- `latitude`, `longitude`
- `password`

선택 필드:

- `address`, `detail_address`
- `tags`: JSON 문자열 배열 또는 쉼표 구분 문자열
- `images`: 최대 5개, 각 5MB 이하 JPEG·PNG·WebP
- `allow_duplicate`: 기본값 `false`

같은 이름의 장소가 50m 이내에 있으면 `409`와 `DUPLICATE_PLACE_WARNING`을 반환합니다. 사용자가 후보를 확인한 뒤 동일 요청에 `allow_duplicate=true`를 넣어 재전송하면 등록됩니다.

## 수정·삭제

- `PUT /api/places/{id}`: multipart 요청, `password` 필수
- `DELETE /api/places/{id}`: JSON 본문 `{"password":"..."}`
- `DELETE /api/places/{placeId}/images/{imageId}`: JSON 본문에 비밀번호 전달

원본 JSON에서 적재된 `source=dataset` 장소는 어떤 비밀번호로도 수정·삭제할 수 없습니다. 사용자 장소의 비밀번호는 교육 요구사항에 따라 평문으로 저장하지만 API 응답에는 포함하지 않습니다.
