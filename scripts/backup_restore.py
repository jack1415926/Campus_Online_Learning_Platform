"""Local experiment backup and restore. Never overwrite the working database."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CALLER_DIR = Path.cwd()
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

from sqlalchemy.engine import make_url
from app.config import settings
from app.services.storage_service import STORAGE_DIR
from setup_local import connect, check_instance, STATE


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def local_state():
    url = make_url(settings.database_url)
    if (url.host, url.port, url.database, url.username) != ("127.0.0.1", 3309, "campus_learning", "campus_app") or settings.storage_backend != "local":
        raise ValueError("This script supports only the project's local MySQL and file storage.")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    with connect(state["root_password"]) as db:
        version = check_instance(db)
    return state, url, version


def counts(db, database):
    with db.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE'", (database,))
        tables = [row[0] for row in cursor.fetchall()]
        result = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM `{database}`.`{table.replace('`', '``')}`")
            result[table] = cursor.fetchone()[0]
    return result


def samples(db, database):
    queries = {
        "course": "SELECT id,title FROM courses ORDER BY id LIMIT 1",
        "attachment": "SELECT id,homework_id,attachment_key,score FROM homework_submissions WHERE attachment_key IS NOT NULL ORDER BY id LIMIT 1",
        "grade": "SELECT id,total_score,max_score,is_pass,answers FROM exam_records WHERE status='graded' ORDER BY id LIMIT 1",
        "certificate": "SELECT id,number,student_name,course_title,platform_name,exam_record_id FROM certificates ORDER BY id LIMIT 1",
    }
    with db.cursor() as cursor:
        cursor.execute(f"USE `{database}`")
        result = {}
        for name, query in queries.items():
            cursor.execute(query)
            row = cursor.fetchone()
            result[name] = list(row) if row else None
    return result


def mysql_command(state, url, program, user, password, arguments, **streams):
    binary = Path(state["mysql_bin"]) / (program + ".exe")
    env = dict(os.environ, MYSQL_PWD=password)
    result = subprocess.run([str(binary), "--host=127.0.0.1", "--port=3309", "--protocol=TCP", f"--user={user}",
        "--default-character-set=utf8mb4", *arguments], env=env, stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), **streams)
    if result.returncode:
        raise RuntimeError(f"{program} failed: " + result.stderr.decode("utf-8", errors="replace")[:1000])


def backup(args):
    state, url, version = local_state()
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", 20081)) == 0:
            raise ValueError("Stop the campus application first; keep MySQL running.")
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d-%H%M%S")
    output = (CALLER_DIR / args.output if args.output else ROOT / "backups" / stamp).resolve()
    if not output.is_relative_to((ROOT / "backups").resolve()) or output == (ROOT / "backups").resolve():
        raise ValueError("Backup output must be a new subdirectory of this project's backups/.")
    output.mkdir(parents=True, exist_ok=False)
    sql = output / "database.sql"
    with sql.open("wb") as stream:
        mysql_command(state, url, "mysqldump", url.username, url.password,
            ["--single-transaction", "--skip-lock-tables", "--no-tablespaces", "--set-gtid-purged=OFF", "--hex-blob", url.database], stdout=stream)
    storage = Path(STORAGE_DIR)
    if any(p.is_symlink() for p in storage.rglob("*")):
        raise ValueError("Uploads contain symbolic links; inspect them before backup.")
    if storage.exists():
        shutil.copytree(storage, output / "storage")
    else:
        (output / "storage").mkdir()
    files = {p.relative_to(output).as_posix(): {"bytes": p.stat().st_size, "sha256": digest(p)}
        for p in sorted(output.rglob("*")) if p.is_file()}
    with connect(state["root_password"]) as db:
        row_counts = counts(db, url.database)
        sample_rows = samples(db, url.database)
    manifest = {"format": 1, "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "mysql_version": version, "database": url.database, "files": files, "row_counts": row_counts, "samples": sample_rows}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"backup": str(output), "files": len(files), "tables": len(row_counts)}, ensure_ascii=False))


def restore(args):
    state, url, _ = local_state()
    if not re.fullmatch(r"campus_restore_[a-zA-Z0-9_]{1,40}", args.database):
        raise ValueError("Use a new isolated database named campus_restore_<name>.")
    if args.confirm_target != args.database:
        raise ValueError("Pass --confirm-target with the exact target database name.")
    source = (CALLER_DIR / args.backup).resolve()
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != 1 or manifest.get("database") != "campus_learning":
        raise ValueError("Unsupported backup manifest.")
    for name, info in manifest["files"].items():
        path = (source / name).resolve()
        if not path.is_relative_to(source) or not path.is_file() or digest(path) != info["sha256"]:
            raise ValueError(f"Backup file is missing or changed: {name}")
    # Ignore no additional upload files silently: copy only the verified file list.
    expected = set(manifest["files"])
    actual = {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file() and p != source / "manifest.json"}
    if actual != expected or "database.sql" not in expected:
        raise ValueError("Backup file list does not match the manifest.")
    target = (ROOT / ".runtime" / "restores" / args.database).resolve()
    restore_root = (ROOT / ".runtime" / "restores").resolve()
    if not target.is_relative_to(restore_root) or target.exists():
        raise ValueError("Restore directory already exists or is outside the restore area.")
    print(f"Restore target database: {args.database}; uploads: {target / 'storage'}", flush=True)
    with connect(state["root_password"]) as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s", (args.database,))
            if cursor.fetchone():
                raise ValueError("Target database already exists; existing databases are never overwritten.")
            cursor.execute(f"CREATE DATABASE `{args.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
    target.mkdir(parents=True)
    shutil.copytree(source / "storage", target / "storage")
    with (source / "database.sql").open("rb") as stream:
        mysql_command(state, url, "mysql", "root", state["root_password"], ["--binary-mode", args.database], stdin=stream, stdout=subprocess.DEVNULL)
    with connect(state["root_password"]) as db:
        restored_counts = counts(db, args.database)
        restored_samples = samples(db, args.database)
    if restored_counts != manifest["row_counts"]:
        raise RuntimeError("Restored table counts differ; keep the isolated target for inspection.")
    if restored_samples != manifest["samples"]:
        raise RuntimeError("Restored course, attachment, grade or certificate sample differs.")
    attachment = restored_samples.get("attachment")
    if attachment:
        attachment_path = (target / "storage" / attachment[2]).resolve()
        if not attachment_path.is_relative_to(target / "storage") or not attachment_path.is_file():
            raise RuntimeError("Restored homework attachment record has no matching upload.")
    for name, info in manifest["files"].items():
        if name.startswith("storage/") and digest(target / name) != info["sha256"]:
            raise RuntimeError(f"Restored upload differs: {name}")
    report = {"database": args.database, "storage": str(target / "storage"), "backup": str(source),
        "row_counts": restored_counts, "samples_verified": [k for k, v in restored_samples.items() if v],
        "files_verified": len(manifest["files"]), "restored_at": datetime.now(timezone(timedelta(hours=8))).isoformat()}
    (target / "restore-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"restored_database": args.database, "tables_verified": len(restored_counts), "files_verified": len(manifest["files"]), "report": str(target / "restore-result.json")}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("backup")
    create.add_argument("--output", help="New directory under this project's backups/ (use an absolute path).")
    load = commands.add_parser("restore")
    load.add_argument("--backup", required=True, help="Absolute path to the backup directory.")
    load.add_argument("--database", required=True)
    load.add_argument("--confirm-target", required=True)
    args = parser.parse_args()
    try:
        (backup if args.command == "backup" else restore)(args)
    except (ValueError, RuntimeError) as error:
        parser.exit(1, str(error)+"\n")


if __name__ == "__main__":
    main()
