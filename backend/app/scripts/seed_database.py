import argparse
import json

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.seed import seed_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="서울 JSON 데이터를 SQLite에 적재합니다.")
    parser.add_argument("--reset", action="store_true", help="기존 테이블을 삭제하고 다시 생성합니다.")
    args = parser.parse_args()
    settings = get_settings()

    if args.reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        report = seed_dataset(session, settings.data_directory)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

