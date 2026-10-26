"""统一存储服务：本地文件系统 与 阿里云 OSS 一键切换。

通过 config 中的 storage_backend("local"/"oss") 决定使用哪种存储。
对外提供 upload / get_url / delete 三个统一接口，业务层无需感知存储方式。
"""

import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 本地存储实现
# ---------------------------------------------------------------------------
# 与 main.py 中 /storage 静态服务的目录保持一致(backend/storage)
# storage_service.py 位于 backend/app/services/，上一级 app/ 的上级即 backend/
STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "storage",
)


def _ensure_storage_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)


def _local_upload(storage_key: str, content: bytes) -> None:
    _ensure_storage_dir()
    file_path = os.path.join(STORAGE_DIR, storage_key)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)


def _local_upload_stream(storage_key: str, fileobj) -> None:
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


def _local_get_url(storage_key: str) -> str:
    return f"/storage/{storage_key}"


def _local_delete(storage_key: str) -> None:
    file_path = os.path.join(STORAGE_DIR, storage_key)
    if os.path.isfile(file_path):
        os.remove(file_path)


# ---------------------------------------------------------------------------
# 阿里云 OSS 实现
# ---------------------------------------------------------------------------
def _get_oss_bucket():
    import oss2  # 延迟导入，仅在使用 OSS 时加载

    auth = oss2.Auth(settings.oss_access_key, settings.oss_secret_key)
    return oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)


def _oss_upload(storage_key: str, content: bytes, content_type: str | None = None) -> None:
    bucket = _get_oss_bucket()
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    bucket.put_object(storage_key, content, headers=headers)


def _oss_upload_stream(storage_key: str, fileobj, content_type: str | None = None) -> None:
    """OSS 流式上传：fileobj 直接传给 oss2，分块读取上传，不占大内存。"""
    bucket = _get_oss_bucket()
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    # oss2 put_object 对 file-like 对象流式读取(内部按 chunk 读取上传)
    bucket.put_object(storage_key, fileobj, headers=headers)


def _oss_get_url(storage_key: str) -> str:
    """OSS 私有 bucket 下返回带签名的临时 URL。"""
    bucket = _get_oss_bucket()
    url = bucket.sign_url("GET", storage_key, settings.oss_signed_url_expire)
    # 若配置了自定义公网域名，把默认域名替换为自定义域名
    if settings.oss_public_domain:
        url = url.replace(
            f"{settings.oss_bucket}.{settings.oss_endpoint}", settings.oss_public_domain
        )
    return url


def _oss_delete(storage_key: str) -> None:
    bucket = _get_oss_bucket()
    bucket.delete_object(storage_key)


# ---------------------------------------------------------------------------
# 统一接口
# ---------------------------------------------------------------------------
def upload(storage_key: str, content: bytes, content_type: str | None = None) -> None:
    """上传内容到当前配置的存储后端(小文件/内存数据)。"""
    if settings.storage_backend == "oss":
        _oss_upload(storage_key, content, content_type)
        logger.info("OSS 上传成功: %s", storage_key)
    else:
        _local_upload(storage_key, content)
        logger.info("本地存储成功: %s", storage_key)


def upload_fileobj(storage_key: str, fileobj, content_type: str | None = None) -> None:
    """流式上传文件对象到存储后端(适合大文件，分块读取不占大内存)。

    fileobj 须为可读的 file-like 对象(如 UploadFile.file)。
    """
    # 确保从文件头开始读
    try:
        fileobj.seek(0)
    except (AttributeError, OSError):
        pass
    if settings.storage_backend == "oss":
        _oss_upload_stream(storage_key, fileobj, content_type)
        logger.info("OSS 流式上传成功: %s", storage_key)
    else:
        _local_upload_stream(storage_key, fileobj)
        logger.info("本地流式存储成功: %s", storage_key)


def get_url(storage_key: str) -> str:
    """返回给定 storage_key 的可访问 URL（OSS 为签名临时 URL）。"""
    if settings.storage_backend == "oss":
        return _oss_get_url(storage_key)
    return _local_get_url(storage_key)


def delete(storage_key: str) -> None:
    """从当前配置的存储后端删除对象。"""
    try:
        if settings.storage_backend == "oss":
            _oss_delete(storage_key)
        else:
            _local_delete(storage_key)
        logger.info("存储对象已删除: %s", storage_key)
    except Exception:
        logger.exception("删除存储对象失败: %s", storage_key)


def is_oss() -> bool:
    """当前是否使用 OSS 存储。"""
    return settings.storage_backend == "oss"
