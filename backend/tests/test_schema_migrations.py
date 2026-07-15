from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.db.session import migrate_legacy_emotion_checkins


def test_satisfaction_column_migration_preserves_checkin(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE places (id INTEGER PRIMARY KEY)
            """
        )
        connection.exec_driver_sql("INSERT INTO places (id) VALUES (1)")
        connection.exec_driver_sql(
            """
            CREATE TABLE emotion_checkins (
                id INTEGER PRIMARY KEY,
                place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
                fingerprint_hash VARCHAR(64) NOT NULL,
                before_emotion VARCHAR(50) NOT NULL,
                before_intensity INTEGER NOT NULL,
                after_emotion VARCHAR(50) NOT NULL,
                after_intensity INTEGER NOT NULL,
                travel_style VARCHAR(100) NOT NULL,
                satisfaction INTEGER NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO emotion_checkins VALUES
            (1, 1, 'fingerprint', '지침', 4, '회복', 5, '가볍게 산책', 5, CURRENT_TIMESTAMP)
            """
        )

    assert migrate_legacy_emotion_checkins(engine) is True
    assert "satisfaction" not in {
        column["name"] for column in inspect(engine).get_columns("emotion_checkins")
    }
    with engine.connect() as connection:
        row = connection.exec_driver_sql(
            "SELECT before_emotion, after_emotion, travel_style FROM emotion_checkins"
        ).one()
    assert row == ("지침", "회복", "가볍게 산책")
    assert migrate_legacy_emotion_checkins(engine) is False
