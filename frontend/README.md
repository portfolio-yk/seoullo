# Seoullo Frontend

Vue 3, Vite, TypeScript 기반의 모바일 우선 SPA입니다.

## 실행과 빌드

저장소 루트에서 실행합니다.

```powershell
pnpm install
pnpm --dir frontend dev
pnpm --dir frontend build
```

로컬 개발 시 `/api` 요청은 기본적으로 `http://localhost:8000`으로 프록시됩니다.

## 환경 변수

| 변수 | 용도 |
|---|---|
| `VITE_API_BASE_URL` | 배포된 Backend origin. 예: `https://seoullo-api.onrender.com` |
| `VITE_KAKAO_JAVASCRIPT_KEY` | Kakao 지도 JavaScript 키 |
| `VITE_API_PROXY_TARGET` | 로컬 Vite 프록시 대상. 기본값 `http://localhost:8000` |

## 주요 경로

| 경로 | 화면 |
|---|---|
| `/` | 장소 검색·목록 |
| `/places/:id` | 장소 상세, 리뷰, 태그 |
| `/places/new` | 사용자 장소 등록 |
| `/places/:id/edit` | 사용자 장소 수정 |
| `/map` | 현재 위치와 장소 지도 |
| `/emotions` | 감정 기반 장소 추천 |
| `/places/:id/checkin` | 선택한 장소의 여행 후 감정 체크인 |
| `/bookmarks` | 로컬 북마크 목록 |

챗봇과 새 장소 등록 플로팅 버튼은 메인과 장소 상세 화면에서만 표시됩니다. Netlify 설정은 [배포 가이드](../docs/deployment.md)를 참고하세요.
