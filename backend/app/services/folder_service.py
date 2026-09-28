"""One-level, metadata-only reconciliation for a folder.

The media volume is never modified here. Media decoding belongs to the
thumbnail worker, so a first visit can return file rows promptly.
"""

import hashlib
import mimetypes
import os
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings
from app.database.database import SessionLocal
from app.database.models import Folder, Image
from app.utils.logger import logger
from sqlalchemy.orm import load_only


@dataclass
class ReconcileResult:
    scanned: bool = False
    discovered: int = 0
    updated: int = 0
    error: str | None = None


class FolderService:
    _locks: dict[int, threading.Lock] = {}
    _registry_lock = threading.Lock()

    @classmethod
    def _folder_lock(cls, folder_id: int) -> threading.Lock:
        with cls._registry_lock:
            return cls._locks.setdefault(folder_id, threading.Lock())

    @staticmethod
    def _version(path: str, size: int, mtime_ns: int) -> str:
        payload = f"v2\0{path}\0{size}\0{mtime_ns}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _media_type(name: str) -> str | None:
        mime = mimetypes.guess_type(name)[0]
        if mime:
            return mime
        if name.lower().endswith((".heic", ".heif")):
            return "image/heic"
        return None

    def reconcile_folder(self, folder_id: int, *, force: bool = False,
                         priority: int = 0, retry_failed: bool = False) -> ReconcileResult:
        result = ReconcileResult()
        with self._folder_lock(folder_id):
            with SessionLocal() as db:
                folder = db.get(Folder, folder_id)
                if folder is None or folder.missing_since is not None:
                    result.error = "目录不存在于索引中"
                    return result
                if (not force and folder.last_scanned_at is not None
                        and datetime.utcnow() - folder.last_scanned_at
                        < timedelta(seconds=settings.FOLDER_RESCAN_SECONDS)):
                    if priority:
                        promoted = db.query(Image).filter(
                            Image.folder_id == folder_id,
                            Image.thumbnail_status.in_(("pending", "failed")),
                            Image.thumbnail_priority < priority,
                        ).update({Image.thumbnail_priority: priority}, synchronize_session=False)
                        if promoted:
                            db.commit()
                    return result
                relative_folder = folder.folder_path

            absolute_folder = settings.IMAGES_DIR / relative_folder
            files: dict[str, tuple[int, int, str | None]] = {}
            directories: dict[str, str] = {}
            try:
                with os.scandir(absolute_folder) as entries:
                    for entry in entries:
                        rel = os.path.relpath(entry.path, settings.IMAGES_DIR)
                        if entry.is_dir(follow_symlinks=False):
                            if not entry.name.startswith((".", "@", "$")):
                                directories[rel] = entry.name
                        elif (entry.is_file(follow_symlinks=False)
                              and entry.name.lower().endswith(tuple(settings.SUPPORTED_FORMATS))):
                            stat = entry.stat(follow_symlinks=False)
                            files[rel] = (stat.st_size, stat.st_mtime_ns,
                                          self._media_type(entry.name))
            except (OSError, ValueError) as exc:
                logger.warning("目录扫描失败 folder_id=%s: %s", folder_id, exc)
                result.error = "目录读取失败，已保留原索引"
                return result

            with SessionLocal() as db:
                folder = db.get(Folder, folder_id)
                existing_files = {
                    image.file_path: image
                    for image in db.query(Image).options(load_only(
                        Image.id, Image.file_path, Image.size_bytes, Image.mtime_ns,
                        Image.thumbnail_path, Image.converted_path, Image.thumbnail_status,
                        Image.thumbnail_version, Image.missing_since,
                    )).filter(Image.folder_id == folder_id)
                }
                existing_folders = {
                    child.folder_path: child
                    for child in db.query(Folder).filter(Folder.parent_id == folder_id)
                }
                # If a mounted media root disappears and Docker exposes an empty
                # directory, do not interpret that as a mass deletion.
                if (relative_folder == "." and not files and not directories
                        and (existing_files or existing_folders)):
                    result.error = "媒体根目录突然为空，已保留原索引"
                    logger.error(result.error)
                    return result

                now = datetime.utcnow()
                for path, name in directories.items():
                    child = existing_folders.get(path)
                    if child is None:
                        db.add(Folder(folder_path=path, name=name, parent_id=folder_id))
                    else:
                        if child.missing_since is not None:
                            self._set_subtree_missing(db, path, None)
                for path, child in existing_folders.items():
                    if path not in directories and child.missing_since is None:
                        self._set_subtree_missing(db, path, now)

                for path, (size, mtime_ns, mime) in files.items():
                    version = self._version(path, size, mtime_ns)
                    image = existing_files.get(path)
                    if image is None:
                        db.add(Image(
                            folder_id=folder_id, file_path=path, mime_type=mime,
                            image_type="video" if mime and mime.startswith("video/") else "original",
                            is_heic=path.lower().endswith((".heic", ".heif")),
                            size_bytes=size, mtime_ns=mtime_ns,
                            thumbnail_version=version, thumbnail_status="pending",
                            thumbnail_priority=priority, thumbnail_attempts=0,
                        ))
                        result.discovered += 1
                        continue
                    image.missing_since = None
                    was_unindexed = image.mtime_ns is None
                    changed = (image.size_bytes is not None and
                               (image.size_bytes != size or image.mtime_ns != mtime_ns))
                    image.size_bytes = size
                    image.mtime_ns = mtime_ns
                    image.mime_type = mime
                    image.is_heic = path.lower().endswith((".heic", ".heif"))
                    thumbnail_missing = (not image.thumbnail_path or not (
                        settings.THUMBNAIL_DIR / image.thumbnail_path
                    ).is_file())
                    legacy_stale = False
                    if was_unindexed and image.thumbnail_path and not thumbnail_missing:
                        try:
                            legacy_stale = (
                                (settings.THUMBNAIL_DIR / image.thumbnail_path).stat().st_mtime_ns
                                < mtime_ns
                            )
                        except OSError:
                            legacy_stale = True
                    converted_missing = (image.is_heic and (
                        not image.converted_path or not (
                            settings.CONVERTED_DIR / image.converted_path
                        ).is_file()
                    ))
                    cache_lost = (image.thumbnail_status == "ready" and
                                  (thumbnail_missing or converted_missing))
                    requested_retry = retry_failed and image.thumbnail_status == "failed"
                    if changed or legacy_stale or cache_lost or requested_retry:
                        image.thumbnail_status = "pending"
                        image.thumbnail_priority = priority
                        image.thumbnail_attempts = 0
                        image.thumbnail_error = None
                        image.thumbnail_retry_at = None
                        result.updated += 1
                    elif image.thumbnail_status == "pending" and image.thumbnail_version is None:
                        # An existing cache from before this migration remains valid.
                        image.thumbnail_status = "ready"
                    image.thumbnail_version = version

                for path, image in existing_files.items():
                    if path not in files and image.missing_since is None:
                        image.missing_since = now
                folder.last_scanned_at = now
                db.commit()
                result.scanned = True
        return result

    @staticmethod
    def _set_subtree_missing(db, path: str, missing_since: datetime | None) -> None:
        root = db.query(Folder).filter(Folder.folder_path == path).first()
        if root is None:
            return
        descendants = []
        queue = deque([root])
        while queue:
            folder = queue.popleft()
            descendants.append(folder)
            queue.extend(db.query(Folder).filter(Folder.parent_id == folder.id).all())
        ids = [folder.id for folder in descendants]
        for folder in descendants:
            folder.missing_since = missing_since
            folder.last_scanned_at = None
        if ids:
            db.query(Image).filter(Image.folder_id.in_(ids)).update(
                {Image.missing_since: missing_since}, synchronize_session=False
            )
