# Seoullo DDL 정의서

## 1. 문서 정보

| 항목 | 내용 |
|---|---|
| DBMS | SQLite 3 |
| ORM | SQLAlchemy 2 |
| 마이그레이션 | Alembic |
| 기준 리비전 | `20260715_0003` |
| 신규 테이블 | `place_emotion_profiles` |
| 관계 | `places` 1 : 0..1 `place_emotion_profiles` |

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

## 3. `place_emotion_profiles`

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

## 4. 실행 DDL

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

## 5. 적재 규칙

1. `contentid`로 `places.content_id`를 찾아 `place_id`를 결정합니다.
2. `emotion`의 그룹과 한글 키가 정의된 양식과 정확히 일치해야 합니다.
3. JSON 초기값은 정수 `0~5`만 허용합니다.
4. 기존 장소에 프로필이 없으면 새로 생성하지만, 이미 존재하는 프로필은 서버 시작 시 덮어쓰지 않습니다.
5. DB 전체 재구축 명령에서는 JSON 기준값으로 새 프로필을 만듭니다.
6. 장소 삭제 시 해당 프로필도 자동 삭제됩니다.

마이그레이션 파일은 `backend/alembic/versions/20260715_0002_place_emotion_profiles.py`입니다.

## 6. `emotion_checkins`

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
