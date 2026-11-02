"""Verify the destructive migration only against a named isolated restored database."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"campus_restore_[A-Za-z0-9_]{1,40}", args.database):
        raise ValueError("Only an isolated campus_restore_* database may be tested.")
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.engine import make_url
    from app.config import settings
    from app.models import Base

    app_url = make_url(settings.database_url)
    assert (app_url.host, app_url.port, app_url.database) == ("127.0.0.1", 3309, "campus_learning")
    credentials = json.loads((ROOT / ".runtime/mysql/credentials.json").read_text(encoding="utf-8"))
    test_url = app_url.set(database=args.database, username="root", password=credentials["root_password"])
    settings.database_url = test_url.render_as_string(hide_password=False)
    engine = create_engine(test_url, hide_parameters=True)
    config = Config(str(ROOT / "backend/alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend/alembic"))
    removed = {"organizations", "job_levels", "positions", "training_plans", "plan_courses", "learning_paths", "path_courses", "notification_templates"}
    ignored = {"users": {"department_id", "job_level", "position"}, "course_assignments": {"training_plan_id"}}

    def fingerprints():
        result = {}
        with engine.connect() as connection:
            schema = inspect(connection)
            for table in sorted(set(schema.get_table_names()) - removed - {"alembic_version"}):
                columns = [c["name"] for c in schema.get_columns(table) if c["name"] not in ignored.get(table, set())]
                selection = ",".join(f"`{c}`" for c in columns)
                rows = sorted(json.dumps(list(row), default=str, ensure_ascii=False) for row in connection.execute(text(f"SELECT {selection} FROM `{table}`")))
                result[table] = {"rows": len(rows), "sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest()}
        return result

    def expect_rejection(fragment):
        try:
            command.upgrade(config, "f9a0b1c2d3e4")
        except RuntimeError as error:
            assert fragment in str(error), str(error)
        else:
            raise AssertionError("Migration unexpectedly allowed deletion")
        assert len(inspect(engine).get_table_names()) == 36
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "e8f9a0b1c2d3"

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "e8f9a0b1c2d3"
    marker = str(uuid.uuid4())
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO job_levels (id,name) VALUES (:id,'migration_guard')"), {"id": marker})
    expect_rejection("nonempty legacy table")
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM job_levels WHERE id=:id"), {"id": marker})
        uid = connection.scalar(text("SELECT id FROM users ORDER BY id LIMIT 1"))
        connection.execute(text("UPDATE users SET job_level='migration_guard' WHERE id=:id"), {"id": uid})
    expect_rejection("users.job_level")
    with engine.begin() as connection:
        connection.execute(text("UPDATE users SET job_level=NULL WHERE id=:id"), {"id": uid})
        assignment = connection.scalar(text("SELECT id FROM course_assignments ORDER BY id LIMIT 1"))
        connection.execute(text("UPDATE course_assignments SET assignment_type='department' WHERE id=:id"), {"id": assignment})
    expect_rejection("Non-user assignments")
    with engine.begin() as connection:
        connection.execute(text("UPDATE course_assignments SET assignment_type='user' WHERE id=:id"), {"id": assignment})
    # Compare after fixture cleanup; require exact preservation across all DDL operations.
    before = fingerprints()
    command.upgrade(config, "f9a0b1c2d3e4")
    assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
    assert len(Base.metadata.tables) == 27
    assert fingerprints() == before
    command.downgrade(config, "e8f9a0b1c2d3")
    assert len(inspect(engine).get_table_names()) == 36
    assert fingerprints() == before
    command.upgrade(config, "f9a0b1c2d3e4")
    assert len(inspect(engine).get_table_names()) == 28
    assert fingerprints() == before
    result = {"status": "PASS", "database": args.database, "tables_before": 36, "tables_after": 28,
              "retained_tables_checked": len(before), "checks": ["nonempty legacy table rejected before DDL", "nonempty removed field rejected before DDL", "non-user assignment rejected before DDL", "upgrade/downgrade/upgrade", "retained data row counts and fingerprints unchanged"]}
    (ROOT / ".runtime/prune-legacy-20261102/migration-check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    engine.dispose()


if __name__ == "__main__":
    main()
