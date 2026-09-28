"""Inventory and safely remove unreferenced generated media files."""

import argparse
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings
from app.database.database import SessionLocal
from app.database.models import Image


_THUMBNAIL = re.compile(r"^.+_[0-9a-f]{8,24}_thumb\.jpg$")
_CONVERTED = re.compile(r"^.+_[0-9a-f]{8,24}\.jpg$")


class CacheMaintenance:
    def run(self, *, dry_run: bool = True) -> dict[str, int | bool]:
        cutoff = datetime.utcnow() - timedelta(days=settings.CACHE_GC_MIN_AGE_DAYS)
        with SessionLocal() as db:
            rows = db.query(Image.thumbnail_path, Image.converted_path,
                            Image.missing_since).all()
        if not rows and not dry_run:
            raise RuntimeError("图片索引为空，拒绝清理缓存")

        references = {"thumbnails": set(), "converted": set()}
        for thumb, converted, missing_since in rows:
            if missing_since is not None and missing_since < cutoff:
                continue
            if thumb:
                references["thumbnails"].add(thumb)
            if converted:
                references["converted"].add(converted)

        report: dict[str, int | bool] = {
            "dry_run": dry_run, "files_seen": 0, "referenced": 0,
            "unreferenced": 0, "eligible_files": 0, "eligible_bytes": 0,
            "deleted_files": 0, "deleted_bytes": 0, "missing_references": 0,
        }
        roots = {
            "thumbnails": settings.THUMBNAIL_DIR,
            "converted": settings.CONVERTED_DIR,
        }
        eligible: list[tuple[Path, int]] = []
        seen_by_kind = {kind: 0 for kind in roots}
        matched_by_kind = {kind: 0 for kind in roots}
        for kind, root in roots.items():
            if root.is_symlink() or not root.is_dir():
                if not dry_run:
                    raise RuntimeError(f"缓存目录不可安全访问: {kind}")
                continue
            root_resolved = root.resolve()
            for reference in references[kind]:
                if not (root / reference).is_file():
                    report["missing_references"] += 1
            pattern = _THUMBNAIL if kind == "thumbnails" else _CONVERTED
            for directory, _, filenames in os.walk(root, followlinks=False):
                for filename in filenames:
                    if not pattern.fullmatch(filename):
                        continue
                    path = Path(directory) / filename
                    if path.is_symlink() or not path.resolve().is_relative_to(root_resolved):
                        continue
                    relative = path.relative_to(root).as_posix()
                    report["files_seen"] += 1
                    seen_by_kind[kind] += 1
                    if relative in references[kind]:
                        report["referenced"] += 1
                        matched_by_kind[kind] += 1
                        continue
                    report["unreferenced"] += 1
                    try:
                        stat = path.stat()
                    except FileNotFoundError:
                        continue
                    if datetime.utcfromtimestamp(stat.st_mtime) >= cutoff:
                        continue
                    report["eligible_files"] += 1
                    report["eligible_bytes"] += stat.st_size
                    eligible.append((path, stat.st_size))
        if not dry_run:
            if report["files_seen"] and not report["referenced"]:
                raise RuntimeError("缓存与数据库没有任何匹配引用，拒绝清理")
            for kind in roots:
                if references[kind] and seen_by_kind[kind] and not matched_by_kind[kind]:
                    raise RuntimeError(f"{kind} 缓存与数据库没有匹配引用，拒绝清理")
            for path, size in eligible:
                if path.is_symlink():
                    continue
                try:
                    path.unlink()
                except FileNotFoundError:
                    continue
                report["deleted_files"] += 1
                report["deleted_bytes"] += size
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect generated cache files")
    parser.add_argument("action", choices=("report", "apply"))
    args = parser.parse_args()
    print(CacheMaintenance().run(dry_run=args.action != "apply"))
