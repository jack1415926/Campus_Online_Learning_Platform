"""Course materials and homework attachments stored on the local filesystem."""

import logging
import os


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 本地存储实现
# ---------------------------------------------------------------------------
# Files are served through authenticated media and attachment endpoints.
STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "storage",
)


def _ensure_storage_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)


def upload_fileobj(storage_key: str, fileobj, content_type: str | None = None) -> None:
    """分块流式写入本地文件，避免一次性载入内存(适配大文件)。"""
    _ensure_storage_dir()
    file_path = os.path.join(STORAGE_DIR, storage_key)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        while True:
            chunk = fileobj.read(1024 * 1024)  # 1MB 分块
            if not chunk:
                break
            f.write(chunk)


def delete(storage_key: str) -> None:
    file_path = os.path.join(STORAGE_DIR, storage_key)
    if os.path.isfile(file_path):
        os.remove(file_path)
