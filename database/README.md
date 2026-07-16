# SQLite Database

로컬 기본 DB 파일은 `database/seoullo.db`입니다. DB 파일은 Git에 포함하지 않으며, 서버가 시작될 때 원본 JSON을 중복 안전하게 다시 적재합니다. Render에서도 영속 디스크를 사용하지 않으므로 재배포 후 같은 과정으로 복구됩니다.

- 원본 JSON 장소는 `source=dataset`이며 수정·삭제하지 않습니다.
- 사용자 장소는 `source=user`이며 평문 비밀번호로 수정·삭제 권한을 확인합니다.
- 사용자 업로드 이미지는 최대 5MB이며 `place_images.data` BLOB으로 저장합니다.
- 원본 IP와 User-Agent는 저장하지 않고 HMAC 식별값만 리뷰·좋아요 중복 방지에 사용합니다.
- 여행코스의 빈 주소는 서버 시작 시 Kakao 역지오코딩으로 보강합니다.
- 보강 주소는 DB에만 저장하고 원본 JSON은 유지합니다.

전체 테이블과 제약조건은 [DDL 정의서](../docs/ddl-definition.md)를 참고하세요.
