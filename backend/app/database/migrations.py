"""Small additive migration for databases created by earlier SimplePhotos releases."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


_COLUMNS = {
    "folders": {
        "last_scanned_at": "TIMESTAMP NULL",
        "missing_since": "TIMESTAMP NULL",
    },
    "images": {
        "size_bytes": "BIGINT NULL",
        "mtime_ns": "BIGINT NULL",
        "missing_since": "TIMESTAMP NULL",
        "thumbnail_status": "VARCHAR(16) NOT NULL DEFAULT 'pending'",
        "thumbnail_version": "VARCHAR(64) NULL",
        "thumbnail_priority": "INTEGER NOT NULL DEFAULT 0",
        "thumbnail_attempts": "INTEGER NOT NULL DEFAULT 0",
        "thumbnail_error": "TEXT NULL",
        "thumbnail_started_at": "TIMESTAMP NULL",
        "thumbnail_retry_at": "TIMESTAMP NULL",
    },
}


def ensure_schema(engine: Engine) -> None:
    """Preserve rows and IDs while adding fields required for incremental work."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        legacy_thumbnail_status = False
        for table, definitions in _COLUMNS.items():
            existing = {column["name"] for column in inspector.get_columns(table)}
            if table == "images":
                legacy_thumbnail_status = "thumbnail_status" not in existing
            for name, definition in definitions.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
        if legacy_thumbnail_status:
            connection.execute(text(
                "UPDATE images SET thumbnail_status = 'ready' "
                "WHERE thumbnail_path IS NOT NULL AND thumbnail_status = 'pending'"
            ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_images_thumbnail_status "
            "ON images (thumbnail_status, thumbnail_priority, thumbnail_retry_at)"
        ))
