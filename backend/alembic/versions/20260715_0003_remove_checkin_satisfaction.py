"""Remove unused emotion check-in satisfaction.

Revision ID: 20260715_0003
Revises: 20260715_0002
Create Date: 2026-07-15
"""

import sqlalchemy as sa
from alembic import op


revision = "20260715_0003"
down_revision = "20260715_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "emotion_checkins" not in inspector.get_table_names():
        return
    if "satisfaction" not in {column["name"] for column in inspector.get_columns("emotion_checkins")}:
        return
    with op.batch_alter_table("emotion_checkins", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_checkin_satisfaction", type_="check")
        batch_op.drop_column("satisfaction")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "emotion_checkins" not in inspector.get_table_names():
        return
    if "satisfaction" in {column["name"] for column in inspector.get_columns("emotion_checkins")}:
        return
    with op.batch_alter_table("emotion_checkins", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("satisfaction", sa.Integer(), nullable=False, server_default="5"))
        batch_op.create_check_constraint("ck_checkin_satisfaction", "satisfaction BETWEEN 1 AND 5")
