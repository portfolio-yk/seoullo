# Seoullo 챗봇 통합 구조

## 처리 흐름

1. 서버가 빈 질문, 서울 외 지역, 실시간 정보, 미제공 운영 정보, 프롬프트 공격을 먼저 차단한다.
2. GPT-5 mini 질의 계획기가 질문을 카테고리, 세부 장소 유형, 자치구, 검색 명사와 고정 감정 선택지로 구조화한다.
3. 서버 규칙 분석 결과와 AI 계획을 합치며, AI가 질문에 없던 검색 명사를 추가하지 못하도록 검증한다.
4. 일반 장소 질문은 `title`, `content_type`, 태그, 주소, 설명으로 만든 한국어 sparse vector를 `seoullo-lexical`에서 검색한다.
5. 감정 질문은 16차원 감정 Pinecone을 우선 검색하고, 장소 조건이 함께 있으면 lexical 결과와 RRF로 결합한다.
6. Pinecone 장애·결과 부족 시 감정 벡터는 SQLite 코사인 계산, 장소 검색은 SQLite 키워드 검색으로 대체한다.
7. OpenAI 임베딩 장소 검색은 별도 권한이 있고 기능 플래그가 켜진 경우에만 추가로 시도한다.
8. 검색된 장소를 `query`, `status`, `documents` 형태의 내부 RAG 계약으로 직렬화한다.
9. GPT-5 mini Responses API의 구조화 출력으로 답변, 의도, 인용 장소, 추천 이유를 생성한다.
10. 서버가 모델이 반환한 모든 장소 ID를 검색 결과와 대조한다.
11. 근거 밖 ID, 파싱 실패, 시간 초과 또는 API 오류가 발생하면 데이터 기반 규칙 응답으로 대체한다.

`공원`, `미술관`, `박물관`, `공연장`, `시장`, `호텔`처럼 상위 카테고리보다 구체적인 표현은
장소 유형 사전으로 해석한다. 구체적인 검색어가 일치하지 않을 때에는 관련 없는 인기 장소로
대체하지 않고 `NO_RESULT`로 처리한다.

## RAG 문서 메타데이터

각 문서는 다음 정보를 포함한다.

- 내부 장소 ID와 `content_id`
- 장소명, 카테고리, 주소, 설명
- 공공 데이터 또는 사용자 등록 장소 구분
- 감정 프로필에서 산출한 상위 감정 키워드
- 태그, 좌표, 좋아요, 조회수, 별점과 리뷰 수
- 검색 결과 순위

문서의 설명이나 사용자 등록 글에 지시문처럼 보이는 문자열이 있어도 모델 명령으로 취급하지 않는다.

## API 응답

`POST /api/chat/messages`는 다음 정보를 반환한다.

- `answer`: 최종 답변
- `intent`: 장소 추천, 감정 추천, 축제, 위치, 커뮤니티, 일반 정보, 알 수 없음
- `retrieval_method`: Pinecone, SQLite 키워드, SQLite 인기순 또는 검색 생략
- `answer_source`: OpenAI 또는 규칙 응답
- `recommendations`: 최대 3개의 장소와 추천 이유·감정 키워드
- `sources`: 서버가 검증한 실제 장소 카드
- `fallback`: 지원 범위 밖이거나 근거가 부족한 응답인지 여부

장소 ID는 출처 카드 이동과 서버 검증을 위한 구조화 필드로만 유지한다. `answer`와 추천
`reason`에 `place_id`, `content_id` 같은 내부 식별자가 생성되더라도 서버가 제거한 뒤 반환한다.

`retrieval_method`의 감정 검색 값은 다음과 같다.

- `pinecone_lexical`: 자체 한국어 sparse vector로 장소 lexical 검색
- `pinecone_emotion`: AI가 해석한 감정 선택지를 기존 16차원 Pinecone 인덱스에서 검색
- `pinecone_hybrid`: lexical 순위와 감정 순위를 RRF로 결합
- `sqlite_emotion`: 같은 16차원 코사인 유사도를 SQLite 감정 프로필에서 계산한 대체 경로

## 임베딩을 사용할 수 없는 환경

`CHAT_SEMANTIC_SEARCH_ENABLED=false`이어도 일반 장소 질의는 임베딩 없는 `seoullo-lexical/places`
sparse 인덱스를 사용한다. lexical 인덱스가 없거나 Pinecone 연결이 실패한 경우에만 SQLite 검색으로 전환한다.
자연어 감정 질의는 일반 임베딩과 무관하게 GPT-5 mini가 고정 감정 선택지를 계획하고 기존 16차원
감정 Pinecone 인덱스를 검색하므로 `우울`, `기분전환`, `피곤`, `편하게 쉬고 싶다` 같은 표현을
처리할 수 있다.

## 자동 검증 범위

- 자치구·카테고리·커뮤니티 검색
- 감정 프로필 점수 기반 검색 순위
- 모델의 근거 밖 장소 ID 차단
- 서울 외 지역, 날씨, 운영시간, 프롬프트 공격, 빈 질문 fallback
- 공공 데이터와 사용자 등록 장소 출처 구분
- 최대 3개 추천 및 감정 키워드 전달
- 공원·미술관·시장 등 세부 장소 유형의 카테고리 이탈 방지
- 검색 실패 시 무관한 인기 장소 미반환
- 사용자용 답변과 추천 이유의 내부 장소 ID 제거
- 자유로운 감정 문장의 AI 구조화 계획
- 감정 Pinecone 우선 검색 및 SQLite 코사인 유사도 fallback
- 한국어 title·content_type·태그·주소 기반 sparse lexical 검색
- lexical·감정 검색 결과 RRF 결합
