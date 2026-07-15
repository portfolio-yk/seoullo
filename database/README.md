# Database

기본 SQLite 경로는 `database/seoullo.db`입니다. FastAPI 시작 시 항상 `data/서울/서울_*.json`을 읽는 중복 안전 적재기를 실행하므로, DB 복구와 새 카테고리 파일 반영이 자동으로 이루어집니다.

## 핵심 원칙

- 원본 JSON 장소는 `source=dataset`이며 수정·삭제하지 않습니다.
- 사용자 장소는 `source=user`이며 평문 비밀번호로 수정·삭제 권한을 확인합니다.
- 주소가 없는 원본 장소는 최초 상세 조회 시 Kakao 역지오코딩 결과를 DB에만 보강합니다.
- 업로드 이미지는 `place_images.data` BLOB에 저장합니다.
- 원본 IP와 User-Agent는 저장하지 않고 HMAC 식별자만 좋아요·리뷰 중복 방지에 사용합니다.

상세 테이블 설명은 `docs/database-schema.md`를 참고하세요.
