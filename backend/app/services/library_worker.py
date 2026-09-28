"""Bounded thumbnail processing and low-rate directory reconciliation."""

import os
import threading
from collections import deque
from datetime import datetime, timedelta
from time import monotonic

from app.config import settings
from app.database.database import SessionLocal
from app.database.models import Folder, Image, ScanRun
from app.services.folder_service import FolderService
from app.services.image_service import ImageService
from app.utils.logger import logger
from sqlalchemy import and_, or_


class LibraryWorker:
    def __init__(self):
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()
        self.threads: list[threading.Thread] = []
        self.folder_service = FolderService()

    def start(self) -> None:
        with SessionLocal() as db:
            db.query(Image).filter(Image.thumbnail_status == "processing").update(
                {Image.thumbnail_status: "pending", Image.thumbnail_started_at: None},
                synchronize_session=False,
            )
            db.query(ScanRun).filter(ScanRun.status == "running").update(
                {ScanRun.status: "pending", ScanRun.started_at: None},
                synchronize_session=False,
            )
            db.commit()
        for number in range(max(1, settings.THUMBNAIL_WORKERS)):
            thread = threading.Thread(target=self._thumbnail_loop,
                                      name=f"thumbnail-worker-{number}", daemon=True)
            thread.start()
            self.threads.append(thread)
        scanner = threading.Thread(target=self._scan_loop, name="library-scanner", daemon=True)
        scanner.start()
        self.threads.append(scanner)

    def stop(self) -> None:
        self.stop_event.set()
        self.wake_event.set()
        for thread in self.threads:
            thread.join(timeout=5)

    def wake(self) -> None:
        self.wake_event.set()

    def request_scan(self) -> int:
        with SessionLocal() as db:
            existing = db.query(ScanRun).filter(
                ScanRun.status.in_(("pending", "running"))
            ).order_by(ScanRun.id.desc()).first()
            if existing:
                return existing.id
            run = ScanRun(status="pending")
            db.add(run)
            db.commit()
            run_id = run.id
        self.wake()
        return run_id

    def _thumbnail_loop(self) -> None:
        renderer = ImageService()
        while not self.stop_event.is_set():
            try:
                claimed = self._claim_image()
                if claimed:
                    self._render_image(renderer, claimed)
                    continue
            except Exception:
                logger.exception("缩略图工作线程异常")
            self.wake_event.wait(timeout=2)
            self.wake_event.clear()

    def _claim_image(self) -> tuple[int, str, str, int, int] | None:
        now = datetime.utcnow()
        with SessionLocal() as db:
            query = db.query(Image).filter(
                Image.missing_since.is_(None),
                Image.thumbnail_version.is_not(None),
                Image.size_bytes.is_not(None),
                Image.mtime_ns.is_not(None),
                or_(
                    Image.thumbnail_status == "pending",
                    and_(Image.thumbnail_status == "failed",
                         Image.thumbnail_attempts < settings.THUMBNAIL_MAX_RETRIES,
                         Image.thumbnail_retry_at <= now),
                ),
            ).order_by(Image.thumbnail_priority.desc(), Image.id.asc())
            if settings.DB_TYPE == "postgresql":
                query = query.with_for_update(skip_locked=True)
            image = query.first()
            if image is None:
                return None
            image.thumbnail_status = "processing"
            image.thumbnail_attempts = (image.thumbnail_attempts or 0) + 1
            image.thumbnail_started_at = now
            snapshot = (image.id, image.file_path, image.thumbnail_version,
                        image.size_bytes, image.mtime_ns)
            db.commit()
            return snapshot

    def _render_image(self, renderer: ImageService,
                      snapshot: tuple[int, str, str, int, int]) -> None:
        image_id, path, version, size, mtime_ns = snapshot
        source = settings.IMAGES_DIR / path
        try:
            before = source.stat()
            if before.st_size != size or before.st_mtime_ns != mtime_ns:
                raise RuntimeError("源文件在扫描后发生变化")
            thumbnail, converted, exif = renderer.render(path, version)
            after = source.stat()
            if after.st_size != size or after.st_mtime_ns != mtime_ns:
                raise RuntimeError("源文件在缩略图生成时发生变化")
            with SessionLocal() as db:
                image = db.get(Image, image_id)
                if image and image.thumbnail_version == version and image.missing_since is None:
                    image.thumbnail_path = thumbnail
                    image.converted_path = converted
                    image.exif_data = exif
                    image.thumbnail_status = "ready"
                    image.thumbnail_priority = 0
                    image.thumbnail_error = None
                    image.thumbnail_retry_at = None
                    image.thumbnail_started_at = None
                    db.commit()
        except Exception as exc:
            logger.warning("缩略图生成失败 image_id=%s: %s", image_id, exc)
            with SessionLocal() as db:
                image = db.get(Image, image_id)
                if image and image.thumbnail_version == version:
                    image.thumbnail_status = "failed"
                    image.thumbnail_error = str(exc)[:1000]
                    image.thumbnail_started_at = None
                    minutes = min(60, 2 ** min(image.thumbnail_attempts, 6))
                    image.thumbnail_retry_at = datetime.utcnow() + timedelta(minutes=minutes)
                    db.commit()

    def _scan_loop(self) -> None:
        next_periodic = monotonic() + 60
        next_gc = monotonic() + settings.CACHE_GC_INTERVAL_SECONDS
        while not self.stop_event.is_set():
            try:
                with SessionLocal() as db:
                    pending = db.query(ScanRun).filter(
                        ScanRun.status == "pending"
                    ).order_by(ScanRun.id).first()
                    run_id = pending.id if pending else None
                if run_id is not None:
                    self._scan_tree(run_id)
                    next_periodic = monotonic() + settings.BACKGROUND_SCAN_SECONDS
                    continue
                if monotonic() >= next_periodic:
                    self._scan_tree(None)
                    next_periodic = monotonic() + settings.BACKGROUND_SCAN_SECONDS
                    continue
                if settings.CACHE_GC_ENABLED and monotonic() >= next_gc:
                    next_gc = monotonic() + settings.CACHE_GC_INTERVAL_SECONDS
                    from app.services.cache_maintenance import CacheMaintenance
                    report = CacheMaintenance().run(dry_run=False)
                    logger.info("缓存清理完成: %s", report)
                    continue
            except Exception:
                logger.exception("图库扫描线程异常")
                next_periodic = monotonic() + 60
            self.wake_event.wait(timeout=5)
            self.wake_event.clear()

    def _scan_tree(self, run_id: int | None) -> None:
        with SessionLocal() as db:
            root = db.query(Folder).filter(Folder.folder_path == ".").first()
            if root is None:
                return
            if run_id is not None:
                run = db.get(ScanRun, run_id)
                run.status = "running"
                run.started_at = datetime.utcnow()
                db.commit()
            queue = deque([root.id])
        visited: set[int] = set()
        discovered = updated = scanned = 0
        errors: list[str] = []
        while queue and not self.stop_event.is_set():
            folder_id = queue.popleft()
            if folder_id in visited:
                continue
            visited.add(folder_id)
            result = self.folder_service.reconcile_folder(
                folder_id, force=True, retry_failed=run_id is not None
            )
            if result.error:
                errors.append(f"folder_id={folder_id}: {result.error}")
                if scanned == 0:
                    break
                continue
            scanned += 1
            discovered += result.discovered
            updated += result.updated
            with SessionLocal() as db:
                children = db.query(Folder.id).filter(
                    Folder.parent_id == folder_id, Folder.missing_since.is_(None)
                ).all()
                queue.extend(child_id for (child_id,) in children)
                if run_id is not None and scanned % 10 == 0:
                    run = db.get(ScanRun, run_id)
                    run.folders_scanned = scanned
                    run.images_discovered = discovered
                    run.images_updated = updated
                    db.commit()
            self.wake()
            self.stop_event.wait(settings.SCAN_DIRECTORY_PAUSE_SECONDS)
        if run_id is not None:
            with SessionLocal() as db:
                run = db.get(ScanRun, run_id)
                run.folders_scanned = scanned
                run.images_discovered = discovered
                run.images_updated = updated
                run.error = "; ".join(errors[:5]) if errors else None
                run.status = "pending" if self.stop_event.is_set() else (
                    "partial" if errors else "completed"
                )
                run.finished_at = datetime.utcnow() if not self.stop_event.is_set() else None
                db.commit()
        logger.info("图库核对: folders=%s new=%s changed=%s errors=%s",
                    scanned, discovered, updated, len(errors))
