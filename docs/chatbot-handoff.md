# Seoullo 장소 안내 챗봇 인수인계

## 구현 범위

10단계 챗봇은 전체 챗봇을 대신하는 기능이 아니라, 관광 장소 데이터에 근거해 질의하고 UI를 시험할 수 있는 최소 구현이다. 모든 페이지에서 플로팅 버튼으로 열 수 있으며 대화 내용은 데이터베이스나 로컬 스토리지에 저장하지 않는다. 브라우저를 새로고침하면 대화가 초기화된다.

## API

`POST /api/chat/messages`

요청 예시:

```json
{
  "message": "종로구 관광지 추천해줘",
  "history": [
    { "role": "user", "content": "조용한 곳이 좋아" },
    { "role": "assistant", "content": "원하는 지역이 있나요?" }
  ]
}
```

`history`는 최대 10개, 질문은 최대 500자다. 서버는 대화를 저장하지 않으며 클라이언트가 현재 세션의 최근 대화만 함께 보낸다.

응답 예시:

```json
{
  "answer": "...",
  "retrieval_method": "sqlite_keyword",
  "answer_source": "openai",
  "sources": [
    {
      "id": 10,
      "title": "장소명",
      "content_type": "관광지",
      "address": "서울특별시 ...",
      "image_url": "https://...",
      "source": "dataset"
    }
  ]
}
```

## 검색과 답변 흐름

1. 질문에서 관광 카테고리, 서울 자치구, 커뮤니티 장소 여부와 검색어를 추출한다.
2. `CHAT_SEMANTIC_SEARCH_ENABLED=true`이고 OpenAI 임베딩 및 Pinecone 장소 인덱스가 준비된 경우 Pinecone 의미 검색을 먼저 시도한다.
3. 의미 검색을 사용할 수 없거나 결과가 없으면 SQLite에서 제목, 설명, 주소, 태그를 검색한다. 검색어가 없는 추천 질문은 좋아요와 조회 수가 높은 장소를 사용한다.
4. 검색 결과 최대 5개만 `gpt-5-mini`에 전달한다.
5. 모델은 전달된 장소만 근거로 답하고, 응답의 장소 ID도 검색 결과 안에서만 선택할 수 있다. 구조화 출력 검증이 실패하거나 OpenAI 호출이 실패하면 규칙 기반 안내문으로 대체한다.

현재 데이터에는 축제의 개최일, 운영시간, 가격처럼 구조화되지 않은 값이 있으므로 모델 입력에서 일정은 명시적으로 `null` 처리한다. 따라서 챗봇은 해당 정보를 추측하지 않고 데이터에 없다고 안내해야 한다.

## 환경 설정

```dotenv
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_REASON_TIMEOUT_SECONDS=20
CHAT_SEMANTIC_SEARCH_ENABLED=false
PINECONE_API_KEY=
PINECONE_INDEX_NAME=seoullo
PINECONE_PLACES_NAMESPACE=places
```

현재 프로젝트 API 키는 채팅 모델은 사용할 수 있지만 임베딩 모델 권한이 없어 `CHAT_SEMANTIC_SEARCH_ENABLED=false`가 기본값이다. 임베딩 모델 권한을 받은 뒤 장소 벡터를 `seoullo/places` 네임스페이스에 다시 적재하고 값을 `true`로 변경하면 의미 검색이 활성화된다. 실패 시에도 SQLite 검색으로 자동 전환된다.

## 담당 팀원 확장 지점

- 검색 정책: `backend/app/services/chat.py`의 `retrieve_places`
- 시스템 지침과 구조화 응답: 같은 파일의 `generate_grounded_answer`
- 요청/응답 계약: `backend/app/schemas/chat.py`
- 프론트 UI: `frontend/src/components/ChatWidget.vue`

축제 일정 등 별도 데이터셋을 연결할 때는 검색 결과를 공통 근거 객체로 변환하고, 응답의 출처에 원본 레코드 식별자를 포함시키는 방식으로 확장한다. 모델이 자체 지식으로 빈 필드를 보완하도록 허용하지 않는다.
