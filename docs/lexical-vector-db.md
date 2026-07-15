# Seoullo 한국어 Lexical Vector DB

## 목적

OpenAI 임베딩 모델 없이 서울 장소의 `title`, `content_type`, 태그, 주소와 설명을 Pinecone에서
검색한다. 결과는 챗봇 RAG의 장소 후보로만 사용하며 최종 사실은 SQLite 장소 레코드로 다시 검증한다.

## Pinecone 구성

| 항목 | 값 |
|---|---|
| index | `seoullo-lexical` |
| vector type | `sparse` |
| metric | `dotproduct` |
| namespace | `places` |
| vector id | `place:{places.id}` |
| 최대 non-zero 값 | 900 |

Pinecone metadata에는 `place_id`, `content_id`, `source`, `title`, `content_type_id`,
`content_type`, `region`, `address`, `tags`를 저장한다. 실제 상세 응답은 metadata가 아니라 SQLite에서 조회한다.

## Sparse vector 생성

문자열을 NFKC 정규화하고 한글·영문·숫자 토큰과 2~3글자 n-gram을 만든다. 같은 토큰은
BLAKE2s 32비트 해시를 사용해 항상 같은 unsigned index로 변환한다. 별도 vocabulary 파일이
필요하지 않으므로 서버 재시작이나 전체 재구축 후에도 query와 document 좌표가 동일하다.

| 장소 필드 | 가중치 |
|---|---:|
| `title` | 5.0 |
| `content_type` | 4.0 |
| tags | 3.0 |
| address·detail_address | 2.0 |
| description | 1.0 |

공원·한강공원·수목원, 미술관·갤러리, 숙박·호텔 등 서비스 장소 사전의 동의어를 함께 확장한다.
최종 sparse vector는 L2 정규화해 문장이 긴 장소가 무조건 상위에 노출되지 않게 한다.

## 챗봇 검색

1. GPT-5 mini 질의 계획기가 카테고리, 자치구, 장소명·시설명, 감정 선택지를 구조화한다.
2. 일반 검색은 query sparse vector로 `seoullo-lexical/places`를 조회한다.
3. 감정 검색은 `seoullo-emotions/profiles`의 16차원 vector를 조회한다.
4. 장소 조건과 감정 조건이 함께 있으면 RRF 가중치 lexical 0.3, emotion 0.7로 결합한다.
5. 상위 장소 ID를 SQLite에서 다시 조회하고 최대 5개만 최종 RAG 문서로 만든다.
6. Pinecone 장애 시 SQLite 키워드·코사인 검색으로 전환한다.

## 동기화

- 서버 빌드 또는 수동 재구축: 전체 namespace 삭제 후 SQLite 장소 전체 upsert
- 사용자 장소 생성: 감정 vector와 lexical vector 동시 upsert
- 사용자 장소 수정: 동일 ID의 두 vector 덮어쓰기
- 사용자 장소 삭제: lexical·감정·선택적 semantic vector 삭제
- 감정 체크인: 감정 vector만 갱신

## 명령

```bash
# 현재 SQLite를 유지하고 lexical index만 재구축
python -m app.scripts.rebuild_pinecone --skip-db-reset --lexical-only

# SQLite 초기화와 lexical·감정 index 전체 재구축
python -m app.scripts.rebuild_pinecone
```
