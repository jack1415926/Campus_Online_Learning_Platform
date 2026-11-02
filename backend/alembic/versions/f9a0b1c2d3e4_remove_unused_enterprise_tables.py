"""Remove empty enterprise-only modules after checking all data before MySQL DDL.

Downgrade recreates their empty schema; existing data must be restored from backup.
"""
from alembic import op
import sqlalchemy as sa

revision = "f9a0b1c2d3e4"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None

# Exact previous MySQL definitions, retained so downgrade does not import deleted models.
LEGACY_DDL = {'organizations': 'CREATE TABLE `organizations` (\n'
                  '  `name` varchar(200) NOT NULL,\n'
                  '  `parent_id` char(36) DEFAULT NULL,\n'
                  '  `level` int NOT NULL,\n'
                  '  `sort_order` int NOT NULL,\n'
                  '  `code` varchar(50) DEFAULT NULL,\n'
                  '  `status` varchar(20) NOT NULL,\n'
                  '  `id` char(36) NOT NULL,\n'
                  '  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
                  '  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
                  '  PRIMARY KEY (`id`),\n'
                  '  UNIQUE KEY `ix_organizations_code` (`code`),\n'
                  '  KEY `ix_organizations_name` (`name`),\n'
                  '  KEY `ix_organizations_parent_id` (`parent_id`),\n'
                  '  CONSTRAINT `organizations_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `organizations` '
                  '(`id`)\n'
                  ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci',
 'job_levels': 'CREATE TABLE `job_levels` (\n'
               '  `name` varchar(100) NOT NULL,\n'
               '  `sort_order` int DEFAULT NULL,\n'
               '  `status` varchar(20) DEFAULT NULL,\n'
               '  `id` char(36) NOT NULL,\n'
               '  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
               '  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
               '  PRIMARY KEY (`id`),\n'
               '  UNIQUE KEY `ix_job_levels_name` (`name`)\n'
               ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci',
 'positions': 'CREATE TABLE `positions` (\n'
              '  `name` varchar(100) NOT NULL,\n'
              '  `sort_order` int DEFAULT NULL,\n'
              '  `status` varchar(20) DEFAULT NULL,\n'
              '  `id` char(36) NOT NULL,\n'
              '  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
              '  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
              '  PRIMARY KEY (`id`),\n'
              '  UNIQUE KEY `ix_positions_name` (`name`)\n'
              ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci',
 'training_plans': 'CREATE TABLE `training_plans` (\n'
                   '  `name` varchar(255) NOT NULL,\n'
                   '  `description` text,\n'
                   '  `target_audience` json DEFAULT NULL,\n'
                   '  `start_date` varchar(50) DEFAULT NULL,\n'
                   '  `end_date` varchar(50) DEFAULT NULL,\n'
                   '  `completion_requirement` json DEFAULT NULL,\n'
                   '  `status` varchar(20) NOT NULL,\n'
                   '  `created_by` char(36) DEFAULT NULL,\n'
                   '  `id` char(36) NOT NULL,\n'
                   '  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
                   '  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
                   '  PRIMARY KEY (`id`),\n'
                   '  KEY `ix_training_plans_name` (`name`)\n'
                   ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci',
 'learning_paths': 'CREATE TABLE `learning_paths` (\n'
                   '  `name` varchar(255) NOT NULL,\n'
                   '  `description` text,\n'
                   '  `target_job_level` varchar(50) DEFAULT NULL,\n'
                   '  `target_position` varchar(100) DEFAULT NULL,\n'
                   '  `deadline_days` int DEFAULT NULL,\n'
                   '  `status` varchar(20) NOT NULL,\n'
                   '  `created_by` char(36) DEFAULT NULL,\n'
                   '  `id` char(36) NOT NULL,\n'
                   '  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
                   '  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
                   '  PRIMARY KEY (`id`),\n'
                   '  KEY `ix_learning_paths_name` (`name`)\n'
                   ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci',
 'plan_courses': 'CREATE TABLE `plan_courses` (\n'
                 '  `plan_id` char(36) NOT NULL,\n'
                 '  `course_id` char(36) NOT NULL,\n'
                 '  PRIMARY KEY (`plan_id`,`course_id`),\n'
                 '  KEY `course_id` (`course_id`),\n'
                 '  CONSTRAINT `plan_courses_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) '
                 'ON DELETE CASCADE,\n'
                 '  CONSTRAINT `plan_courses_ibfk_2` FOREIGN KEY (`plan_id`) REFERENCES `training_plans` '
                 '(`id`) ON DELETE CASCADE\n'
                 ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci',
 'path_courses': 'CREATE TABLE `path_courses` (\n'
                 '  `path_id` char(36) NOT NULL,\n'
                 '  `course_id` char(36) NOT NULL,\n'
                 '  `sort_order` int DEFAULT NULL,\n'
                 '  `is_required` tinyint(1) DEFAULT NULL,\n'
                 '  PRIMARY KEY (`path_id`,`course_id`),\n'
                 '  KEY `course_id` (`course_id`),\n'
                 '  CONSTRAINT `path_courses_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) '
                 'ON DELETE CASCADE,\n'
                 '  CONSTRAINT `path_courses_ibfk_2` FOREIGN KEY (`path_id`) REFERENCES `learning_paths` '
                 '(`id`) ON DELETE CASCADE\n'
                 ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci',
 'notification_templates': 'CREATE TABLE `notification_templates` (\n'
                           '  `code` varchar(100) NOT NULL,\n'
                           '  `name` varchar(200) NOT NULL,\n'
                           '  `notification_type` '
                           "enum('system','course_reminder','exam_reminder','assignment','certificate') NOT "
                           'NULL,\n'
                           '  `title_template` varchar(500) NOT NULL,\n'
                           '  `body_template` text NOT NULL,\n'
                           '  `channels` json DEFAULT NULL,\n'
                           "  `trigger_mode` enum('event','scheduled') NOT NULL,\n"
                           '  `is_active` tinyint(1) NOT NULL,\n'
                           '  `id` char(36) NOT NULL,\n'
                           '  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
                           '  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
                           '  PRIMARY KEY (`id`),\n'
                           '  UNIQUE KEY `ix_notification_templates_code` (`code`),\n'
                           '  KEY `ix_notification_templates_notification_type` (`notification_type`)\n'
                           ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci'}

REMOVED_COLUMNS = {"users": ("department_id", "job_level", "position"), "course_assignments": ("training_plan_id",)}


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    # Validate every candidate before the first nontransactional ALTER/DROP.
    for name in LEGACY_DDL:
        if name in tables and connection.scalar(sa.text(f"SELECT COUNT(*) FROM `{name}`")):
            raise RuntimeError(f"Refusing to remove nonempty legacy table: {name}. Export and review its data first.")
    foreign_keys = []
    for table, removed in REMOVED_COLUMNS.items():
        columns = {c["name"] for c in inspector.get_columns(table)}
        for column in removed:
            if column in columns and connection.scalar(sa.text(f"SELECT COUNT(*) FROM `{table}` WHERE `{column}` IS NOT NULL AND `{column}` <> ''")):
                raise RuntimeError(f"Refusing to discard legacy values in {table}.{column}.")
        foreign_keys.extend((table, fk) for fk in inspector.get_foreign_keys(table)
                            if set(fk["constrained_columns"]) & set(removed))
    if connection.scalar(sa.text("SELECT COUNT(*) FROM course_assignments WHERE assignment_type <> 'user'")):
        raise RuntimeError("Non-user assignments require review before removing enterprise assignment types.")
    allowed = {(table, fk["name"]) for table, fk in foreign_keys}
    for table in tables - set(LEGACY_DDL):
        for fk in inspector.get_foreign_keys(table):
            if fk["referred_table"] in LEGACY_DDL and (table, fk["name"]) not in allowed:
                raise RuntimeError(f"Unexpected reference to legacy table from {table}.{fk['name']}.")
    for table, fk in foreign_keys:
        op.drop_constraint(fk["name"], table, type_="foreignkey")
    for table, removed in REMOVED_COLUMNS.items():
        columns = {c["name"] for c in sa.inspect(connection).get_columns(table)}
        for column in removed:
            if column in columns:
                op.drop_column(table, column)
    for name in ("plan_courses", "path_courses", "training_plans", "learning_paths", "notification_templates", "job_levels", "positions", "organizations"):
        if name in tables:
            op.drop_table(name)
    op.alter_column("course_assignments", "assignment_type", type_=sa.Enum("user", name="assignment_type"), existing_nullable=False)


def downgrade():
    connection = op.get_bind()
    for ddl in LEGACY_DDL.values():
        connection.exec_driver_sql(ddl)
    op.add_column("users", sa.Column("department_id", sa.CHAR(36), nullable=True))
    op.add_column("users", sa.Column("job_level", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("position", sa.String(100), nullable=True))
    op.create_index("ix_users_department_id", "users", ["department_id"])
    op.create_foreign_key("users_ibfk_1", "users", "organizations", ["department_id"], ["id"])
    op.add_column("course_assignments", sa.Column("training_plan_id", sa.CHAR(36), nullable=True))
    op.create_foreign_key("course_assignments_ibfk_2", "course_assignments", "training_plans", ["training_plan_id"], ["id"], ondelete="SET NULL")
    op.alter_column("course_assignments", "assignment_type", type_=sa.Enum("user", "department", "user_group", "job_level", "position", name="assignment_type"), existing_nullable=False)
