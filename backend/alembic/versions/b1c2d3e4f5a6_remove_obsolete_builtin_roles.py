"""Remove the enterprise-edition builtin roles that the campus edition does not use.

Only a role that currently grants nothing AND has no user binding is removed, so a
database where the legacy translation in ``seed_rbac`` has not run yet keeps its roles
and keeps its users. ``downgrade`` restores the original four builtin definitions.
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None

# code -> (name, description) as seeded by the enterprise edition.
OBSOLETE_ROLES = {
    "learner": ("普通员工", "查看课程、学习、考试、个人档案"),
    "manager": ("部门管理者", "管理本部门学习进度、分配课程、审批申请"),
    "author": ("内容创作者", "创建和编辑课程内容、提交审核"),
    "sysadmin": ("系统管理员", "系统配置、SSO、日志审计、权限维护"),
}


def upgrade():
    connection = op.get_bind()
    skipped = []
    for code in OBSOLETE_ROLES:
        role_id = connection.scalar(
            sa.text("SELECT id FROM roles WHERE code = :code"), {"code": code}
        )
        if role_id is None:
            continue
        bound_users = connection.scalar(
            sa.text("SELECT COUNT(*) FROM user_roles WHERE role_id = :id"), {"id": role_id}
        )
        granted = connection.scalar(
            sa.text("SELECT COUNT(*) FROM role_permissions WHERE role_id = :id"), {"id": role_id}
        )
        if bound_users or granted:
            # Deleting the role would cascade away the user's binding before seed_rbac can
            # translate it, so leave it for that translation instead of losing access here.
            skipped.append(code)
            continue
        connection.execute(sa.text("DELETE FROM role_permissions WHERE role_id = :id"), {"id": role_id})
        connection.execute(sa.text("DELETE FROM user_roles WHERE role_id = :id"), {"id": role_id})
        connection.execute(sa.text("DELETE FROM roles WHERE id = :id"), {"id": role_id})
    if skipped:
        print(
            "kept legacy roles that still grant permissions or bind users: "
            + ", ".join(sorted(skipped))
        )


def downgrade():
    connection = op.get_bind()
    for code, (name, description) in OBSOLETE_ROLES.items():
        exists = connection.scalar(
            sa.text("SELECT COUNT(*) FROM roles WHERE code = :code"), {"code": code}
        )
        if exists:
            continue
        connection.execute(
            sa.text(
                "INSERT INTO roles (id, code, name, description, is_builtin, created_at, updated_at) "
                "VALUES (:id, :code, :name, :description, 1, NOW(), NOW())"
            ),
            {"id": str(uuid.uuid4()), "code": code, "name": name, "description": description},
        )
