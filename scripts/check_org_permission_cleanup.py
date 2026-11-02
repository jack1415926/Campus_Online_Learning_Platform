"""Check permission migration and reseeding only in an isolated restored database."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"campus_restore_[A-Za-z0-9_]{1,40}", args.database):
        raise ValueError("Only a restored campus_restore_* database may be tested.")
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.core.seed import seed_rbac

    app_url = make_url(settings.database_url)
    assert (app_url.host, app_url.port, app_url.database) == ("127.0.0.1", 3309, "campus_learning")
    state = json.loads((ROOT / ".runtime/mysql/credentials.json").read_text(encoding="utf-8"))
    url = app_url.set(database=args.database, username="root", password=state["root_password"])
    settings.database_url = url.render_as_string(hide_password=False)
    engine = create_engine(url, hide_parameters=True)
    config = Config("alembic.ini")

    def retained():
        with engine.connect() as connection:
            permissions = [tuple(r) for r in connection.execute(text("SELECT id,code,name,module,description FROM permissions WHERE code NOT IN ('org:read','org:manage') ORDER BY id"))]
            bindings = [tuple(r) for r in connection.execute(text("SELECT rp.role_id,rp.permission_id FROM role_permissions rp JOIN permissions p ON p.id=rp.permission_id WHERE p.code NOT IN ('org:read','org:manage') ORDER BY rp.role_id,rp.permission_id"))]
            users = [tuple(r) for r in connection.execute(text("SELECT id,user_id,role_id,data_scope FROM user_roles ORDER BY id"))]
            return permissions, bindings, users

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "f9a0b1c2d3e4"
        assert connection.scalar(text("SELECT COUNT(*) FROM permissions WHERE code IN ('org:read','org:manage')")) == 2
    before = retained()
    command.upgrade(config, "a0b1c2d3e4f5")
    assert retained() == before
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM permissions WHERE code IN ('org:read','org:manage')")) == 0
        assert connection.scalar(text("SELECT COUNT(*) FROM role_permissions rp LEFT JOIN permissions p ON p.id=rp.permission_id WHERE p.id IS NULL")) == 0
    command.downgrade(config, "f9a0b1c2d3e4")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM permissions WHERE code IN ('org:read','org:manage')")) == 2
    command.upgrade(config, "a0b1c2d3e4f5")
    with Session(engine) as db:
        seed_rbac(db)
        db.commit()
        seed_rbac(db)
        db.commit()
    assert retained() == before
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM permissions WHERE code LIKE 'org:%'")) == 0
        total = connection.scalar(text("SELECT COUNT(*) FROM permissions"))
    result = {"status": "PASS", "database": args.database, "permissions_after": total, "checks": ["only organization permissions and their bindings removed", "user-role assignments unchanged", "upgrade/downgrade/upgrade", "two reseeds do not recreate org permissions"]}
    (ROOT / ".runtime/org-permission-cleanup-check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    engine.dispose()


if __name__ == "__main__":
    main()
