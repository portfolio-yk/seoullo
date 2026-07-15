import argparse
import json

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.seed import seed_dataset
from app.services.vector_store import rebuild_emotion_index, rebuild_places_namespace


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite와 Pinecone 인덱스를 다시 구축합니다.")
    parser.add_argument(
        "--skip-db-reset",
        action="store_true",
        help="SQLite 초기화를 건너뛰고 현재 장소 데이터를 사용합니다.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--emotion-only", action="store_true", help="16차원 감정 인덱스만 구축합니다.")
    mode.add_argument("--places-only", action="store_true", help="장소 RAG 인덱스만 구축합니다.")
    args = parser.parse_args()
    settings = get_settings()

    report = None
    if not args.skip_db_reset:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as session:
            report = seed_dataset(session, settings.data_directory)
        print(json.dumps({"sqlite": report.to_dict()}, ensure_ascii=False, indent=2))

    if not args.places_only:
        if report and (report.missing_emotion_items or report.invalid_emotion_items):
            raise SystemExit(
                "감정 인덱스를 구축할 수 없습니다: "
                f"누락 {report.missing_emotion_items}건, 형식 오류 {report.invalid_emotion_items}건"
            )
        emotion_report = rebuild_emotion_index(settings)
        print(json.dumps({"emotion_index": emotion_report.to_dict()}, ensure_ascii=False, indent=2))

    if not args.emotion_only:
        upserted = rebuild_places_namespace(settings)
        print(json.dumps({"place_rag_index": {"upserted": upserted}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
