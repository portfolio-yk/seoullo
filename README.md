# Seoullo

서울 관광 공공데이터와 익명 장소 커뮤니티를 결합한 모바일 중심 서비스입니다.

## 프로젝트 구조

- `frontend/`: Vue 3 + Vite + TypeScript SPA
- `backend/`: FastAPI + SQLAlchemy API
- `database/`: SQLite 데이터베이스와 DB 문서
- `data/서울/`: 한국관광공사 TourAPI 원본 JSON
- `docs/`: 프로젝트 기술 문서

## 빠른 시작

1. 루트의 `.env.example`을 `.env`로 복사하고 필요한 값을 입력합니다.
2. 백엔드 의존성을 설치합니다.
3. `python -m app.scripts.seed_database --reset`으로 초기 DB를 생성합니다.
4. `uvicorn app.main:app --reload`로 백엔드를 실행합니다.
5. 저장소 루트에서 `pnpm install`, `pnpm --filter seoullo-frontend dev`를 실행합니다.

상세 명령과 환경변수는 각 하위 디렉터리의 README를 참고하세요.

## 데이터 출처

이 서비스는 한국관광공사 TourAPI(TourAPI 4.0)의 데이터를 활용합니다.

- 출처: 한국관광공사
- 원본 API: https://www.data.go.kr/data/15101578/openapi.do
- 라이선스: 공공누리 제3유형

원본 JSON은 수정하지 않으며, 카카오 역지오코딩으로 보강된 주소는 SQLite에만 저장합니다.
