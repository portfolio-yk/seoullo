from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()
settings.database_file.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def migrate_legacy_emotion_checkins(bind: Engine) -> bool:
    """Remove the retired satisfaction column while preserving check-in history."""
    inspector = inspect(bind)
    if "emotion_checkins" not in inspector.get_table_names():
        return False
    if "satisfaction" not in {column["name"] for column in inspector.get_columns("emotion_checkins")}:
        return False

    from app.db.models import EmotionCheckin

    columns = (
        "id, place_id, fingerprint_hash, before_emotion, before_intensity, "
        "after_emotion, after_intensity, travel_style, created_at"
    )
    with bind.begin() as connection:
        connection.exec_driver_sql(
            f"CREATE TEMPORARY TABLE emotion_checkins_backup AS "
            f"SELECT {columns} FROM emotion_checkins"
        )
        connection.exec_driver_sql("DROP TABLE emotion_checkins")
        EmotionCheckin.__table__.create(bind=connection)
        connection.exec_driver_sql(
            f"INSERT INTO emotion_checkins ({columns}) "
            f"SELECT {columns} FROM emotion_checkins_backup"
        )
        connection.exec_driver_sql("DROP TABLE emotion_checkins_backup")
    return True


def init_db() -> None:
    # Import model modules before create_all so every table is registered.
    from app.db import models  # noqa: F401

    migrate_legacy_emotion_checkins(engine)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
