"""Media rendering. Database work is handled by the indexer and worker."""

import os
import uuid
from pathlib import Path

from app.config import settings
from app.utils.image_utils import ImageProcessor


class ImageService:
    def __init__(self):
        self.processor = ImageProcessor()

    @staticmethod
    def _cache_name(relative_path: str, version: str, suffix: str) -> str:
        return f"{version[:2]}/media_{version[2:26]}{suffix}"

    @staticmethod
    def _atomic_render(destination: Path, render, source: Path) -> None:
        if destination.is_file():
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f"{destination.name}.{uuid.uuid4().hex}.tmp")
        try:
            render(str(source), str(temporary))
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def render(self, relative_path: str, version: str) -> tuple[str, str | None, dict]:
        """Return cache-relative paths and EXIF only after all outputs are ready."""
        source = settings.IMAGES_DIR / relative_path
        thumbnail_relative = self._cache_name(relative_path, version, "_thumb.jpg")
        thumbnail = settings.THUMBNAIL_DIR / thumbnail_relative
        converted_relative = None
        if source.suffix.lower() in (".heic", ".heif"):
            converted_relative = self._cache_name(relative_path, version, ".jpg")
            converted = settings.CONVERTED_DIR / converted_relative
            self._atomic_render(converted, self.processor.convert_heic, source)
        self._atomic_render(thumbnail, self.processor.create_thumbnail, source)
        return thumbnail_relative, converted_relative, self.processor.get_exif_data(str(source))
