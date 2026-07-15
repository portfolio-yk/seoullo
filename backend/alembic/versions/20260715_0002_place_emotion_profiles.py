"""Add fixed-shape place emotion profiles.

Revision ID: 20260715_0002
Revises: 20260715_0001
Create Date: 2026-07-15
"""

import sqlalchemy as sa
from alembic import op


revision = "20260715_0002"
down_revision = "20260715_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The initial revision in this educational project creates the current
    # SQLAlchemy metadata. A fresh database may therefore already contain this
    # table, while an existing 0001 database does not.
    if "place_emotion_profiles" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "place_emotion_profiles",
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("mood_fatigue", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mood_anxiety", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mood_stifled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mood_excitement", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mood_loneliness", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mood_calm", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("after_recovery", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("after_release", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("after_vitality", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("after_comfort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("after_immersion", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("after_excitement", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("style_quiet_solo", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("style_light_walk", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("style_new_stimulation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("style_together", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mood_fatigue >= 0 AND mood_anxiety >= 0 AND mood_stifled >= 0 "
            "AND mood_excitement >= 0 AND mood_loneliness >= 0 AND mood_calm >= 0",
            name="ck_emotion_profile_mood_nonnegative",
        ),
        sa.CheckConstraint(
            "after_recovery >= 0 AND after_release >= 0 AND after_vitality >= 0 "
            "AND after_comfort >= 0 AND after_immersion >= 0 AND after_excitement >= 0",
            name="ck_emotion_profile_after_nonnegative",
        ),
        sa.CheckConstraint(
            "style_quiet_solo >= 0 AND style_light_walk >= 0 "
            "AND style_new_stimulation >= 0 AND style_together >= 0",
            name="ck_emotion_profile_style_nonnegative",
        ),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("place_id"),
    )
    op.execute(
        """
        INSERT INTO place_emotion_profiles (place_id, created_at, updated_at)
        SELECT id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM places
        WHERE source = 'user'
        """
    )


def downgrade() -> None:
    if "place_emotion_profiles" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("place_emotion_profiles")
