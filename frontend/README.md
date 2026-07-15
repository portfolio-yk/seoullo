# Seoullo Frontend

저장소 루트에서 실행합니다.

```bash
pnpm install
pnpm --filter seoullo-frontend dev
```

환경변수는 `VITE_API_BASE_URL`, `VITE_KAKAO_JAVASCRIPT_KEY`를 사용합니다. 로컬 개발에서는 Vite가 `/api` 요청을 `http://localhost:8000`으로 프록시합니다.

## 화면 경로

- `/`: 장소 검색·카테고리·정렬·목록
- `/places/:id`: 장소 상세
- `/places/new`: 사용자 장소 등록
- `/places/:id/edit`: 사용자 장소 수정

모바일에서는 하단 내비게이션을 사용하며 820px 이상에서는 데스크톱 상단 내비게이션과 다열 카드 레이아웃으로 전환됩니다.
