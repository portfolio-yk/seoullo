# Seoullo 데이터베이스 스키마

## 테이블

| 테이블 | 목적 |
|---|---|
| `data_sources` | 공공데이터 출처와 라이선스 표시 |
| `places` | 원본 및 사용자 등록 장소 |
| `place_images` | 최대 5MB 이미지 BLOB |
| `tags` | 정규화된 태그와 사용 횟수 |
| `place_tags` | 장소와 태그의 다대다 연결 |
| `reviews` | 별점 1~5와 익명 리뷰 |
| `place_likes` | 장소 좋아요 중복 방지 레코드 |
| `review_likes` | 리뷰 좋아요 중복 방지 레코드 |
| `emotion_checkins` | 방문 전후 감정과 여행 스타일 체크인 |
| `place_emotion_profiles` | 장소별 고정 16차원 감정 누적값 |

## 데이터 생명주기

1. 서버 시작 시 스키마를 준비합니다.
2. 전체 `서울_*.json`을 중복 없이 적재하며 이미 존재하는 `content_id`는 건너뜁니다.
3. 사용자 장소·리뷰·체크인은 서비스 운영 중 DB에 저장됩니다.
4. 영속 디스크를 사용하지 않으므로 Render 재시작 후 DB가 사라질 수 있습니다.
5. 새 DB가 생성되면 원본 JSON 장소만 자동 복구됩니다.

## 원본 보존

원본 JSON은 변경하지 않습니다. 역지오코딩 주소는 `places.address`와 `places.address_source`에 별도 저장하며, `address_source`는 `dataset`, `missing`, `kakao` 중 하나로 관리할 예정입니다.
