# Seoullo Backend

FastAPI, SQLAlchemy, SQLite로 구성된 Seoullo API 서버입니다.

## 실행

프로젝트 루트의 `.env`를 읽습니다.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

서버 시작 시 다음 작업을 수행합니다.

1. SQLite 테이블 생성과 호환성 마이그레이션
2. `data/서울/서울_*.json` 중복 안전 적재
3. 주소가 비어 있는 여행코스의 Kakao 역지오코딩 및 DB 저장

Kakao 주소 보강 실패는 서버 시작을 중단하지 않으며 다음 시작 때 다시 시도합니다.

## 관리 명령

```powershell
# DB를 비우고 원본 데이터 재적재
python -m app.scripts.seed_database --reset

# 원본 데이터 검증
python -m app.scripts.validate_data

# DB 재적재 후 lexical·emotion Pinecone 인덱스 재구축
python -m app.scripts.rebuild_pinecone

# DB를 유지한 채 인덱스별 재구축
python -m app.scripts.rebuild_pinecone --skip-db-reset --lexical-only
python -m app.scripts.rebuild_pinecone --skip-db-reset --emotion-only

# OpenAI 임베딩 권한이 있을 때만 사용하는 선택 기능
python -m app.scripts.rebuild_pinecone --skip-db-reset --semantic-only

# 테스트
pytest
```

기본 챗봇 검색은 OpenAI 임베딩 없이 lexical·emotion 인덱스를 사용합니다. 전체 설정과 동기화 규칙은 [아키텍처 문서](../docs/architecture.md), 엔드포인트는 [API 명세](../docs/api.md)를 참고하세요.
