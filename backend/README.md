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
- 테스트: `pytest`

장소 API 요청 형식은 `../docs/place-api.md`에 정리되어 있습니다.

Pinecone 재구축은 `OPENAI_API_KEY`와 `PINECONE_API_KEY`가 모두 설정된 경우에만 실행됩니다.
