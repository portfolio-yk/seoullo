# 사용자 장소 감정 프로필과 여행 후 체크인

## 1. 사용자 장소 생성·수정

사용자 장소는 더 이상 감정 수치 0으로 초기화하지 않는다. 장소명, 카테고리, 설명, 주소, 좌표, 태그를 OpenAI Responses API에 전달하고 Pydantic 구조화 출력으로 16개 기본 감정 수치를 받는다.

- 모델: `gpt-5-mini`
- 값 범위: 각 항목 정수 1~5
- 출력 필드: `place_emotion_profiles`의 고정 16개 컬럼
- 추론 강도: `minimal`
- 출력 토큰 상한: 2,000
- 저장 옵션: `store=false`

생성 요청은 다음 순서로 처리한다.

1. 장소와 태그, 이미지를 SQLite 트랜잭션에 준비한다.
2. OpenAI가 기본 감정 수치 16개를 생성한다.
3. `place_emotion_profiles`에 기본 수치를 기록한다.
4. 감정 인덱스에 16차원 가중 벡터를 필수 upsert한다.
5. API 프로젝트에 임베딩 모델 권한이 있으면 일반 장소 RAG 인덱스에도 1,536차원 임베딩을 upsert한다.
6. 필수 감정 벡터 동기화가 성공한 뒤 SQLite를 commit한다.

수정할 때도 같은 과정을 다시 수행한다. 기존 체크인이 있으면 AI 기본 수치를 새로 만든 뒤 과거 체크인의 선택 횟수를 다시 합산하므로 누적 데이터가 사라지지 않는다.

OpenAI 감정 수치 생성 또는 Pinecone 감정 벡터 처리에 실패하면 SQLite 변경은 rollback되고 API는 `503`을 반환한다. 일반 장소 임베딩 권한이 없는 API 프로젝트에서는 감정 벡터만 반영하며 장소 등록을 막지 않는다.

## 2. 사용자 장소 삭제

비밀번호 검증 후 다음 벡터를 먼저 삭제한다.

- `seoullo` 인덱스 / `places` 네임스페이스 / `place:{place_id}`
- `seoullo-emotions` 인덱스 / `profiles` 네임스페이스 / `emotion:{place_id}`

벡터 삭제가 성공하면 장소를 삭제한다. SQLite의 외래키 `ON DELETE CASCADE`에 따라 감정 프로필과 체크인도 함께 삭제된다.

## 3. 여행 후 감정 체크인

API:

```http
POST /api/emotions/checkins
```

요청 예시:

```json
{
  "place_id": 105,
  "before_emotion": "지침",
  "before_intensity": 4,
  "after_emotion": "회복",
  "after_intensity": 5,
  "travel_style": "가볍게 산책"
}
```

저장 항목은 방문 장소, 방문 전 감정과 강도, 방문 후 감정과 강도, 여행 스타일, 작성 시각, 익명 브라우저 지문 해시다. 원본 IP와 브라우저 문자열은 저장하지 않는다.

제출 시 선택된 다음 세 컬럼만 각각 1씩 증가한다.

- `mood.{before_emotion}`
- `afterFeeling.{after_emotion}`
- `style.{travel_style}`

강도는 체크인 이력에 저장하지만 감정 프로필 증가량은 요구사항대로 항상 1이다. 증가된 프로필로 16차원 감정 벡터를 다시 계산해 Pinecone에 upsert하고, 성공한 뒤 체크인과 DB 프로필을 commit한다. Pinecone 반영 실패 시 체크인과 증가분을 모두 rollback한다.

## 4. 프론트엔드

장소 상세의 `다녀왔어요 · 여행 후 감정 체크인`에서 체크인 화면으로 이동한다.

1. 방문 전 감정 한 개와 강도 1~5
2. 방문 후 감정 한 개와 강도 1~5
3. 여행 스타일 한 개

성공 화면에서는 증가한 세 키워드와 Pinecone 반영 완료를 안내하고, 장소 상세 또는 감정 추천으로 이동할 수 있다.
