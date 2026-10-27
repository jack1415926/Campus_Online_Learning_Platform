"""Two fixed platform settings."""
from alembic import op
import sqlalchemy as sa
from app.config import settings

revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table("platform_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_name", sa.String(100), nullable=False),
        sa.Column("registration_open", sa.Boolean(), nullable=False))
    op.bulk_insert(table, [{"id": 1, "platform_name": settings.app_name, "registration_open": True}])


def downgrade():
    op.drop_table("platform_settings")
