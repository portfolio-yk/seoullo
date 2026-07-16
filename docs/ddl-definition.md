# Seoullo DDL 정의서

## 1. 문서 정보

| 항목 | 내용 |
|---|---|
| DBMS | SQLite 3 |
| ORM | SQLAlchemy 2 |
| 마이그레이션 | Alembic |
| 기준 리비전 | `20260715_0003` |
| 테이블 수 | 10 |
| 스키마 생성 | 서버 시작 시 `Base.metadata.create_all`, 배포 변경 이력은 Alembic 관리 |

## 2. 전체 테이블 목록

| 테이블 | 용도 |
|---|---|
| `data_sources` | 공공데이터 출처와 라이선스 |
| `places` | 데이터셋 및 사용자 등록 장소 |
| `place_images` | 사용자 업로드 이미지 BLOB |
| `tags` | 정규화된 태그와 사용 횟수 |
| `place_tags` | 장소와 태그의 다대다 연결 |
| `reviews` | 장소별 별점 리뷰 |
| `place_likes` | 장소 좋아요 중복 방지 기록 |
| `review_likes` | 리뷰 좋아요 중복 방지 기록 |
| `emotion_checkins` | 여행 후 감정 체크인 이력 |
| `place_emotion_profiles` | 장소별 고정 16차원 감정 누적값 |

## 3. 출처와 장소

### `data_sources`

| 컬럼 | 타입 | 제약/설명 |
|---|---|---|
| `id` | INTEGER | PK |
| `region` | VARCHAR(50) | 지역명, UNIQUE |
| `provider` | VARCHAR | 제공 기관 |
| `dataset_name` | VARCHAR(200) | 데이터셋명 |
| `source_url` | VARCHAR | 원본 안내 URL |
| `license_name` | VARCHAR | 라이선스명 |
| `license_url` | VARCHAR(500) | 라이선스 안내 URL |
| `notice` | TEXT | 출처·이용 조건 |

### `places`

모든 기능의 기준 테이블입니다. `source`가 `dataset`이면 원본 JSON, `user`이면 사용자 등록 장소입니다.

| 컬럼 그룹 | 주요 컬럼 | 설명 |
|---|---|---|
| 식별 | `id`, `source`, `content_id`, `region` | PK, 원본 ID, 출처 구분, 지역 |
| 기본 정보 | `title`, `content_type`, `content_type_id`, `description`, `telephone` | 장소 표시 정보 |
| 주소 | `address`, `detail_address`, `zipcode`, `address_source` | 원본·사용자·역지오코딩 주소 |
| 위치 | `latitude`, `longitude`, `map_level` | 지도와 거리 계산 |
| 이미지 | `primary_image_url`, `thumbnail_url`, `copyright_code` | 데이터셋 이미지 URL |
| 분류 | `area_code`, `sigungu_code`, `category1~3`, `classification1~3`, `legal_dong_*` | 원본 분류 코드 |
| 권한 | `password` | 사용자 장소의 평문 수정·삭제 비밀번호, 데이터셋은 NULL |
| 집계 | `like_count`, `view_count`, `review_count`, `rating_sum` | 목록·상세 표시용 집계값 |
| 시간 | `source_created_time`, `source_modified_time`, `created_at`, `updated_at` | 원본 및 서비스 시각 |

주요 제약은 다음과 같습니다.

- `source`는 `dataset` 또는 `user`입니다.
- `content_id`는 원본·사용자 장소를 포함해 고유하게 관리합니다.
- 위도·경도는 장소 등록 시 필수입니다.
- `address_source`는 `dataset`, `user`, `missing`, `kakao_reverse` 중 현재 생성 경로에 맞는 값을 사용합니다.
- 장소 삭제 시 이미지·태그 연결·리뷰·좋아요·감정 프로필·체크인이 연쇄 삭제됩니다.
- 데이터 출처는 장소별 FK가 아니라 `places.region`과 `data_sources.region`을 논리적으로 연결합니다.

## 4. 이미지와 태그

### `place_images`

| 컬럼 | 타입 | 제약/설명 |
|---|---|---|
| `id` | INTEGER | PK |
| `place_id` | INTEGER | FK → `places.id`, ON DELETE CASCADE |
| `filename` | VARCHAR | 원본 파일명 |
| `media_type` | VARCHAR | 이미지 MIME 타입 |
| `size_bytes` | INTEGER | 바이트 크기, DB CHECK 제한 5MB |
| `data` | BLOB | 이미지 본문 |
| `sort_order` | INTEGER | 장소 내 이미지 순서, 장소별 UNIQUE |
| `created_at` | DATETIME | 생성 시각 |

### `tags`, `place_tags`

`tags`는 정규화된 이름을 고유하게 저장하고 `place_tags`가 장소와 태그를 다대다로 연결합니다. `(place_id, tag_id)`는 UNIQUE입니다. 애플리케이션에서 장소당 최대 10개, 태그당 6자 이하를 검증합니다.

## 5. 리뷰와 좋아요

### `reviews`

| 컬럼 | 타입 | 제약/설명 |
|---|---|---|
| `id` | INTEGER | PK |
| `place_id` | INTEGER | FK → `places.id`, ON DELETE CASCADE |
| `rating` | INTEGER | 1~5 |
| `content` | TEXT | 리뷰 내용 |
| `password` | VARCHAR | 평문 수정·삭제 비밀번호 |
| `fingerprint_hash` | VARCHAR(64) | 익명 중복 방지 식별값 |
| `like_count` | INTEGER | 기본값 0 |
| `created_at`, `updated_at` | DATETIME | 작성·수정 시각 |

`(place_id, fingerprint_hash)`는 UNIQUE이므로 같은 익명 식별값은 장소당 리뷰 하나만 작성할 수 있습니다.

### `place_likes`, `review_likes`

각 테이블은 대상 FK와 `fingerprint_hash`, 생성 시각을 저장합니다. `(대상 ID, fingerprint_hash)` UNIQUE 제약으로 중복 좋아요를 방지합니다. 식별값은 IP와 User-Agent 원문이 아니라 `FINGERPRINT_SECRET`을 이용한 HMAC 결과입니다.

## 6. `place_emotion_profiles`

장소마다 최대 한 행만 존재합니다. 데이터셋 장소는 JSON의 `emotion` 객체에서 초기값을 받고, 사용자 장소는 OpenAI 구조화 응답으로 생성한 1~5 기본값을 받습니다. 체크인 단계에서는 선택된 감정 컬럼만 1씩 증가하므로 운영 중 값은 5를 초과할 수 있습니다. 사용자 장소 수정 시 기본값을 다시 생성한 후 기존 체크인 횟수를 재합산합니다.

| 컬럼 | 타입 | NULL | 기본값 | 키/제약 | JSON 경로 |
|---|---|---:|---:|---|---|
| `place_id` | INTEGER | N | - | PK, FK → `places.id`, ON DELETE CASCADE | `contentid`로 장소 연결 |
| `mood_fatigue` | INTEGER | N | 0 | `>= 0` | `emotion.mood.지침` |
| `mood_anxiety` | INTEGER | N | 0 | `>= 0` | `emotion.mood.불안` |
| `mood_stifled` | INTEGER | N | 0 | `>= 0` | `emotion.mood.답답함` |
| `mood_excitement` | INTEGER | N | 0 | `>= 0` | `emotion.mood.설렘` |
| `mood_loneliness` | INTEGER | N | 0 | `>= 0` | `emotion.mood.외로움` |
| `mood_calm` | INTEGER | N | 0 | `>= 0` | `emotion.mood.평온함` |
| `after_recovery` | INTEGER | N | 0 | `>= 0` | `emotion.afterFeeling.회복` |
| `after_release` | INTEGER | N | 0 | `>= 0` | `emotion.afterFeeling.해방` |
| `after_vitality` | INTEGER | N | 0 | `>= 0` | `emotion.afterFeeling.활력` |
| `after_comfort` | INTEGER | N | 0 | `>= 0` | `emotion.afterFeeling.위로` |
| `after_immersion` | INTEGER | N | 0 | `>= 0` | `emotion.afterFeeling.몰입` |
| `after_excitement` | INTEGER | N | 0 | `>= 0` | `emotion.afterFeeling.설렘` |
| `style_quiet_solo` | INTEGER | N | 0 | `>= 0` | `emotion.style.조용히 혼자` |
| `style_light_walk` | INTEGER | N | 0 | `>= 0` | `emotion.style.가볍게 산책` |
| `style_new_stimulation` | INTEGER | N | 0 | `>= 0` | `emotion.style.새로운 자극` |
| `style_together` | INTEGER | N | 0 | `>= 0` | `emotion.style.누군가와 함께` |
| `created_at` | DATETIME | N | 애플리케이션 UTC 시각 | - | - |
| `updated_at` | DATETIME | N | 애플리케이션 UTC 시각 | 수정 시 갱신 | - |

## 7. 감정 프로필 실행 DDL

```sql
CREATE TABLE place_emotion_profiles (
    place_id INTEGER NOT NULL,
    mood_fatigue INTEGER NOT NULL DEFAULT 0,
    mood_anxiety INTEGER NOT NULL DEFAULT 0,
    mood_stifled INTEGER NOT NULL DEFAULT 0,
    mood_excitement INTEGER NOT NULL DEFAULT 0,
    mood_loneliness INTEGER NOT NULL DEFAULT 0,
    mood_calm INTEGER NOT NULL DEFAULT 0,
    after_recovery INTEGER NOT NULL DEFAULT 0,
    after_release INTEGER NOT NULL DEFAULT 0,
    after_vitality INTEGER NOT NULL DEFAULT 0,
    after_comfort INTEGER NOT NULL DEFAULT 0,
    after_immersion INTEGER NOT NULL DEFAULT 0,
    after_excitement INTEGER NOT NULL DEFAULT 0,
    style_quiet_solo INTEGER NOT NULL DEFAULT 0,
    style_light_walk INTEGER NOT NULL DEFAULT 0,
    style_new_stimulation INTEGER NOT NULL DEFAULT 0,
    style_together INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (place_id),
    FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
    CONSTRAINT ck_emotion_profile_mood_nonnegative CHECK (
        mood_fatigue >= 0 AND mood_anxiety >= 0 AND mood_stifled >= 0
        AND mood_excitement >= 0 AND mood_loneliness >= 0 AND mood_calm >= 0
    ),
    CONSTRAINT ck_emotion_profile_after_nonnegative CHECK (
        after_recovery >= 0 AND after_release >= 0 AND after_vitality >= 0
        AND after_comfort >= 0 AND after_immersion >= 0 AND after_excitement >= 0
    ),
    CONSTRAINT ck_emotion_profile_style_nonnegative CHECK (
        style_quiet_solo >= 0 AND style_light_walk >= 0
        AND style_new_stimulation >= 0 AND style_together >= 0
    )
);
```

## 8. 감정 프로필 적재 규칙

1. `contentid`로 `places.content_id`를 찾아 `place_id`를 결정합니다.
2. `emotion`의 그룹과 한글 키가 정의된 양식과 정확히 일치해야 합니다.
3. JSON 초기값은 정수 `0~5`만 허용합니다.
4. 기존 장소에 프로필이 없으면 새로 생성하지만, 이미 존재하는 프로필은 서버 시작 시 덮어쓰지 않습니다.
5. DB 전체 재구축 명령에서는 JSON 기준값으로 새 프로필을 만듭니다.
6. 장소 삭제 시 해당 프로필도 자동 삭제됩니다.

마이그레이션 파일은 `backend/alembic/versions/20260715_0002_place_emotion_profiles.py`입니다.

## 9. `emotion_checkins`

체크인은 방문 전후 감정과 강도, 여행 스타일을 이력으로 저장합니다. 사용되지 않던 `satisfaction` 컬럼은 `20260715_0003`에서 제거했습니다.

| 컬럼 | 타입 | NULL | 키/제약 |
|---|---|---:|---|
| `id` | INTEGER | N | PK |
| `place_id` | INTEGER | N | FK → `places.id`, ON DELETE CASCADE |
| `fingerprint_hash` | VARCHAR(64) | N | 익명 브라우저 지문 해시, INDEX |
| `before_emotion` | VARCHAR(50) | N | 방문 전 감정 |
| `before_intensity` | INTEGER | N | 1~5 |
| `after_emotion` | VARCHAR(50) | N | 방문 후 감정 |
| `after_intensity` | INTEGER | N | 1~5 |
| `travel_style` | VARCHAR(100) | N | 여행 스타일 |
| `created_at` | DATETIME | N | 애플리케이션 UTC 시각 |

컬럼 제거 마이그레이션은 `backend/alembic/versions/20260715_0003_remove_checkin_satisfaction.py`입니다.

## 10. 관계 요약

```text
data_sources 1 ── N places          (region 논리 연결)
places       1 ── N place_images
places       N ── N tags             (place_tags)
places       1 ── N reviews
places       1 ── N place_likes
reviews      1 ── N review_likes
places       1 ── 0..1 place_emotion_profiles
places       1 ── N emotion_checkins
```

## 11. 마이그레이션 이력

| 리비전 | 내용 |
|---|---|
| `20260715_0001` | 장소·이미지·태그·리뷰·좋아요·체크인 초기 스키마 |
| `20260715_0002` | `place_emotion_profiles`와 16개 감정 컬럼 추가 |
| `20260715_0003` | 사용하지 않는 `emotion_checkins.satisfaction` 제거 |

SQLite 파일은 배포 산출물이 아닙니다. 서버 재시작 시 스키마와 데이터셋을 재구성하며 사용자 생성 데이터는 영속 디스크가 없을 경우 보존되지 않습니다.
