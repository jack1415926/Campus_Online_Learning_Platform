"""Remove organization permissions and every role binding left by the retired module."""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "a0b1c2d3e4f5"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    ids = connection.execute(sa.text(
        "SELECT id FROM permissions WHERE code IN ('org:read','org:manage')"
    )).scalars().all()
    if ids:
        statement = sa.text("DELETE FROM role_permissions WHERE permission_id IN :ids").bindparams(sa.bindparam("ids", expanding=True))
        connection.execute(statement, {"ids": ids})
        statement = sa.text("DELETE FROM permissions WHERE id IN :ids").bindparams(sa.bindparam("ids", expanding=True))
        connection.execute(statement, {"ids": ids})


def downgrade():
    # Restore the former builtin definitions/admin grants, not custom historical grants.
    connection = op.get_bind()
    admin_id = connection.scalar(sa.text("SELECT id FROM roles WHERE code='admin'"))
    for code, name in (("org:read", "View organizations"), ("org:manage", "Manage organizations")):
        permission_id = connection.scalar(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": code})
        if permission_id is None:
            permission_id = str(uuid.uuid4())
            connection.execute(sa.text("INSERT INTO permissions (id,code,name,module) VALUES (:id,:code,:name,'org')"), {"id": permission_id, "code": code, "name": name})
        if admin_id and not connection.scalar(sa.text("SELECT COUNT(*) FROM role_permissions WHERE role_id=:role AND permission_id=:permission"), {"role": admin_id, "permission": permission_id}):
            connection.execute(sa.text("INSERT INTO role_permissions (role_id,permission_id) VALUES (:role,:permission)"), {"role": admin_id, "permission": permission_id})
