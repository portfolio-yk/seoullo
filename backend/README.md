# Seoullo Backend

## 로컬 실행

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements-dev.txt
python -m app.scripts.seed_database --reset
uvicorn app.main:app --reload
```

Linux/macOS에서는 활성화 명령으로 `source .venv/bin/activate`를 사용합니다.

## 주요 명령

- 초기 DB 생성: `python -m app.scripts.seed_database --reset`
- 데이터 검증: `python -m app.scripts.validate_data`
- Pinecone 전체 재구축: `python -m app.scripts.rebuild_pinecone`
- 임베딩 없는 장소 lexical 인덱스만 재구축: `python -m app.scripts.rebuild_pinecone --skip-db-reset --lexical-only`
- 16차원 감정 인덱스만 재구축: `python -m app.scripts.rebuild_pinecone --skip-db-reset --emotion-only`
- OpenAI 임베딩 장소 인덱스만 재구축: `python -m app.scripts.rebuild_pinecone --skip-db-reset --semantic-only`
- 테스트: `pytest`

장소 API 요청 형식은 `../docs/place-api.md`에 정리되어 있습니다.

기본 재구축은 `PINECONE_API_KEY`만으로 lexical·감정 인덱스를 생성합니다. `OPENAI_API_KEY`와
임베딩 모델 권한은 `--semantic-only` 또는 `CHAT_SEMANTIC_SEARCH_ENABLED=true`인 경우에만 필요합니다.
