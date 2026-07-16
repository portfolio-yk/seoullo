# Netlify·Render 배포 가이드

프론트엔드는 Netlify, 백엔드는 Render 무료 티어에 같은 GitHub 모노레포를 연결하는 기준입니다. 영속 디스크는 사용하지 않습니다.

## Git에 포함할 파일

다음 파일은 루트 워크스페이스 설치와 Netlify 재현 빌드에 필요합니다.

- `package.json`
- `pnpm-workspace.yaml`
- `pnpm-lock.yaml`
- `netlify.toml`
- `frontend/`, `backend/`, `data/`, `database/.gitkeep`

`netlify.toml`의 설정과 Netlify UI 설정이 겹치면 파일 설정이 저장소의 기준이 됩니다. UI에서는 환경 변수만 관리하는 편이 안전합니다. `.pnpm-store/`, `node_modules/`, 빌드 결과, SQLite DB, `.env`, `.agent/`·`.agents/`는 커밋하지 않습니다.

## 1. Render 백엔드

GitHub 저장소로 Web Service를 만들고 다음 값을 사용합니다.

| 항목 | 값 |
|---|---|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/health` |

### Render 환경 변수

| 변수 | 설정 |
|---|---|
| `APP_ENV` | `production` |
| `DATABASE_PATH` | `/tmp/seoullo.db` |
| `FRONTEND_ORIGINS` | Netlify 최종 URL |
| `FINGERPRINT_SECRET` | 충분히 긴 임의 문자열 |
| `KAKAO_REST_API_KEY` | Kakao REST API 키 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `OPENAI_CHAT_MODEL` | 기본값 `gpt-5-mini`, 필요 시만 지정 |
| `PINECONE_API_KEY` | Pinecone API 키 |

다음 값은 코드 기본값과 다르게 쓸 때만 추가합니다.

```dotenv
PINECONE_LEXICAL_INDEX_NAME=seoullo-lexical
PINECONE_EMOTION_INDEX_NAME=seoullo-emotions
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
PINECONE_LEXICAL_NAMESPACE=places
PINECONE_EMOTION_NAMESPACE=profiles
CHAT_SEMANTIC_SEARCH_ENABLED=false
```

기본 구성은 OpenAI 임베딩을 사용하지 않으므로 `OPENAI_EMBEDDING_MODEL`과 semantic 인덱스 설정은 필요하지 않습니다. `OPENAI_API_KEY`는 챗봇 답변, 감정 추천 이유, 사용자 장소의 감정 초깃값 생성에 사용합니다.

무료 인스턴스 재시작·재배포 후 `/tmp`의 DB가 사라질 수 있습니다. 서버 시작 시 원본 JSON을 다시 적재하고 여행코스 주소를 보강하므로 의도한 동작입니다. 사용자 장소·리뷰·체크인은 함께 사라집니다.

## 2. Pinecone 초기 구축

배포 전에 로컬 또는 Render Shell에서 백엔드 환경 변수를 입력한 뒤 실행합니다.

```powershell
cd backend
python -m app.scripts.rebuild_pinecone
```

이 명령은 DB를 원본 데이터 기준으로 다시 만들고 lexical·emotion 인덱스를 초기화해 적재합니다. DB를 유지하면서 한 인덱스만 복구할 때는 다음 명령을 사용합니다.

```powershell
python -m app.scripts.rebuild_pinecone --skip-db-reset --lexical-only
python -m app.scripts.rebuild_pinecone --skip-db-reset --emotion-only
```

## 3. Netlify 프론트엔드

저장소 루트의 `netlify.toml`이 다음 설정을 제공합니다.

| 항목 | 값 |
|---|---|
| Build Command | `pnpm run build:frontend` |
| Publish Directory | `frontend/dist` |
| Node | 22 |
| SPA Redirect | `/*` → `/index.html` |

Netlify 환경 변수를 입력합니다.

| 변수 | 값 |
|---|---|
| `VITE_API_BASE_URL` | Render 서비스 origin. `/api`를 붙이지 않음 |
| `VITE_KAKAO_JAVASCRIPT_KEY` | Kakao JavaScript 키 |

예: `VITE_API_BASE_URL=https://seoullo-api.onrender.com`

## 4. 외부 서비스 도메인 등록

1. Kakao Developers의 JavaScript 플랫폼 도메인에 Netlify URL을 등록합니다.
2. Render의 `FRONTEND_ORIGINS`에 같은 Netlify URL을 등록합니다.
3. 커스텀 도메인을 연결하면 Kakao와 Render 환경 변수도 새 도메인으로 갱신합니다.
4. Render를 먼저 배포하고 `/api/health`를 확인한 뒤 Netlify를 배포합니다.

## 배포 확인

- 메인 목록과 장소 상세 API가 정상 응답하는지 확인
- Kakao 지도와 주소 검색이 허용된 도메인에서 로드되는지 확인
- 챗봇 일반 장소 질의와 감정 질의가 장소 카드를 반환하는지 확인
- 사용자 장소 생성·수정·삭제 시 lexical·emotion 인덱스가 동기화되는지 확인
- 감정 체크인 후 같은 장소의 emotion 인덱스가 갱신되는지 확인
