"""add sessions table

Revision ID: e6f7a8b9c1d2
Revises: d5e6f7a8b9c1
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e6f7a8b9c1d2"
down_revision = "d5e6f7a8b9c1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sessions",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("client_info", sa.String(length=500), nullable=True),
        sa.Column("status", sa.Enum("active", "revoked", "expired", name="session_status"),
                  nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token", "sessions", ["token"])
    op.create_index("ix_sessions_status", "sessions", ["status"])


def downgrade():
    op.drop_index("ix_sessions_status", table_name="sessions")
    op.drop_index("ix_sessions_token", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
