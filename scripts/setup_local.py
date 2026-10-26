"""Prepare a user-owned MySQL instance using the already installed MySQL 8.4.

Run with the project's Python 3.12. No Windows service or elevation is used.
Private configuration and data stay under the ignored .runtime directory.
"""

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.parse import quote

import pymysql


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
RUNTIME = ROOT / ".runtime"
MYSQL = RUNTIME / "mysql"
DATA = MYSQL / "data"
STATE = MYSQL / "credentials.json"
CONFIG = MYSQL / "my.ini"
PORT = 3309
DATABASE = "campus_learning"
APP_USER = "campus_app"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def port_in_use():
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", PORT)) == 0


def connect(password):
    return pymysql.connect(
        host="127.0.0.1", port=PORT, user="root", password=password,
        charset="utf8mb4", connect_timeout=3, autocommit=True,
    )


def check_instance(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT VERSION(), @@port, @@datadir")
        version, port, data_dir = cursor.fetchone()
    if not version.startswith("8.4.") or port != PORT or Path(data_dir).resolve() != DATA.resolve():
        raise RuntimeError("Port 3309 does not belong to this project's MySQL 8.4 instance.")
    return version


def start_database(mysql_bin):
    if not DATA.resolve().is_relative_to(ROOT):
        raise RuntimeError("The runtime data directory must stay inside this project.")
    MYSQL.mkdir(parents=True, exist_ok=True)
    if STATE.exists():
        state = json.loads(STATE.read_text(encoding="utf-8"))
    else:
        if port_in_use() or (DATA.exists() and any(DATA.iterdir())):
            raise RuntimeError("Existing data or port without matching credentials; refusing to overwrite.")
        state = {
            "root_password": secrets.token_urlsafe(32),
            "app_password": secrets.token_urlsafe(32),
            "root_configured": False,
        }
        write_json(STATE, state)

    if not port_in_use():
        executable = mysql_bin / "mysqld.exe"
        version = subprocess.check_output([str(executable), "--version"], text=True)
        if "8.4." not in version:
            raise RuntimeError("Use an existing MySQL 8.4 installation; no download is performed.")
        config_text = (
            "[mysqld]\n"
            f"basedir={mysql_bin.parent.as_posix()}\n"
            f"datadir={DATA.as_posix()}\n"
            "bind-address=127.0.0.1\n"
            f"port={PORT}\n"
            "mysqlx=OFF\n"
            f"log-error={(MYSQL / 'server.log').as_posix()}\n"
            f"pid-file={(MYSQL / 'server.pid').as_posix()}\n"
        )
        CONFIG.write_text(config_text, encoding="utf-8")
        if not (DATA / "mysql.ibd").exists():
            if DATA.exists() and any(DATA.iterdir()):
                raise RuntimeError("Incomplete MySQL data exists; inspect .runtime/mysql/server.log.")
            subprocess.run(
                [str(executable), f"--defaults-file={CONFIG}", "--initialize-insecure"],
                check=True, creationflags=NO_WINDOW,
            )
        with (MYSQL / "console.log").open("ab") as log:
            process = subprocess.Popen(
                [str(executable), f"--defaults-file={CONFIG}"],
                stdout=log, stderr=log, creationflags=NO_WINDOW,
            )
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("MySQL exited; inspect .runtime/mysql/server.log.")
            if port_in_use():
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("MySQL startup timed out; inspect .runtime/mysql/server.log.")

    if state["root_configured"]:
        connection = connect(state["root_password"])
    else:
        try:
            connection = connect(state["root_password"])
        except pymysql.err.OperationalError as exc:
            if exc.args[0] != 1045:
                raise
            connection = connect("")
            check_instance(connection)
            with connection.cursor() as cursor:
                cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (state["root_password"],))
        state["root_configured"] = True
        write_json(STATE, state)

    try:
        version = check_instance(connection)
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            cursor.execute("CREATE USER IF NOT EXISTS 'campus_app'@'127.0.0.1' IDENTIFIED BY %s", (state["app_password"],))
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{DATABASE}`.* TO 'campus_app'@'127.0.0.1'")
    finally:
        connection.close()
    print(f"MySQL {version} ready at 127.0.0.1:{PORT}; application user: {APP_USER}.")
    return state


def configure_application(state):
    env_file = BACKEND / ".env"
    if not env_file.exists():
        env_file.write_text(
            "APP_NAME=校园在线学习平台\nDEBUG=false\n"
            f"DATABASE_URL=mysql+pymysql://{APP_USER}:{quote(state['app_password'], safe='')}@127.0.0.1:{PORT}/{DATABASE}?charset=utf8mb4\n"
            f"SECRET_KEY={secrets.token_urlsafe(48)}\n"
            "STORAGE_BACKEND=local\n"
            'CORS_ORIGINS=["http://127.0.0.1:20081","http://localhost:20081"]\n',
            encoding="utf-8",
        )
    # Verify the effective settings before running migrations against any database.
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    from app.config import settings
    from sqlalchemy.engine import make_url

    url = make_url(settings.database_url)
    if (url.host, url.port, url.database, url.username) != ("127.0.0.1", PORT, DATABASE, APP_USER):
        raise RuntimeError("Effective DATABASE_URL must use this project's campus_app account and database.")
    if url.password != state["app_password"]:
        raise RuntimeError("Application password does not match local instance credentials; existing .env was preserved.")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, check=True)

    from app.auth.local import LocalAuthProvider
    from app.core.seed import assign_role, seed_rbac
    from app.database import SessionLocal
    from app.models.role import DataScope
    from app.models.user import User
    from sqlalchemy import select

    credentials_file = RUNTIME / "admin.json"
    with SessionLocal() as db:
        seed_rbac(db)
        user = db.execute(select(User).where(User.username == "campus_admin")).scalar_one_or_none()
        if user is None:
            password = secrets.token_urlsafe(18)
            user = LocalAuthProvider().register(
                db, username="campus_admin", email="campus_admin@example.com",
                password=password, full_name="校园平台管理员",
            ).user
            assign_role(db, user, "admin", DataScope.company)
            user.requested_role = "admin"
            db.commit()
            write_json(credentials_file, {"username": "campus_admin", "password": password})
        else:
            db.commit()
    print("Migrations and initial application administrator ready. Login details: .runtime/admin.json")


def stop_database():
    if not port_in_use():
        print("This project's database is already stopped.")
        return
    state = json.loads(STATE.read_text(encoding="utf-8"))
    with connect(state["root_password"]) as connection:
        check_instance(connection)
        with connection.cursor() as cursor:
            cursor.execute("SHUTDOWN")
    for _ in range(60):
        if not port_in_use():
            print("This project's MySQL instance stopped.")
            return
        time.sleep(0.5)
    raise RuntimeError("MySQL is still stopping; inspect .runtime/mysql/server.log.")


if __name__ == "__main__":
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Use the existing Python 3.12 environment for this project.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mysql-bin", type=Path, default=Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "MySQL/MySQL Server 8.4/bin")
    parser.add_argument("--stop-db", action="store_true")
    args = parser.parse_args()
    if args.stop_db:
        stop_database()
    else:
        configure_application(start_database(args.mysql_bin.resolve()))
