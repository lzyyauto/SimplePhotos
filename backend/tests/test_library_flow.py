"""Integration checks against an isolated SQLite DB and temporary media tree."""

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

from PIL import Image


BACKEND = Path(__file__).resolve().parents[1]


class LibraryFlowTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="simplephotos-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.images = self.root / "images"
        self.album = self.images / "album"
        self.album.mkdir(parents=True)
        self.env = os.environ.copy()
        self.env.update({
            "DB_TYPE": "sqlite",
            "DATA_ROOT": str(self.root),
            "IMAGES_DIR": str(self.images),
            "FOLDER_RESCAN_SECONDS": "0",
            "BACKGROUND_SCAN_SECONDS": "3600",
            "THUMBNAIL_WORKERS": "1",
            "CACHE_GC_ENABLED": "false",
            "PYTHONPATH": str(BACKEND),
        })

    def start_server(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        log = (self.root / "server.log").open("w")
        self.addCleanup(log.close)
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
             "--port", str(port)],
            cwd=BACKEND, env=self.env, stdout=log, stderr=log,
        )
        self.addCleanup(self.stop_server, process)
        for _ in range(100):
            try:
                self.get("/api/")
                return
            except Exception:
                if process.poll() is not None:
                    break
                time.sleep(0.1)
        self.fail((self.root / "server.log").read_text())

    @staticmethod
    def stop_server(process):
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

    def get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=10) as response:
            return json.load(response)

    def post(self, path):
        request = urllib.request.Request(self.url + path, data=b"", method="POST")
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)

    def folder_id(self, name="album"):
        folders = self.get("/api/folders/1/subfolders")["items"]
        return next(folder["id"] for folder in folders if folder["name"] == name)

    def wait_image(self, folder_id, status="ready"):
        for _ in range(100):
            data = self.get(f"/api/folders/{folder_id}/images")
            if data["items"] and data["items"][0]["thumbnail_status"] == status:
                return data["items"][0]
            time.sleep(0.1)
        self.fail(f"image did not reach {status}")

    def wait_scan(self, run_id):
        for _ in range(100):
            scan = self.get(f"/api/scan/{run_id}")
            if scan["status"] not in ("pending", "running"):
                return scan
            time.sleep(0.1)
        self.fail("scan did not finish")

    def test_first_visit_and_unchanged_rescan(self):
        Image.new("RGB", (80, 80), "red").save(self.album / "one #1.jpg")
        self.start_server()
        folder_id = self.folder_id()
        first = self.get(f"/api/folders/{folder_id}/images")
        self.assertEqual(first["total"], 1)
        ready = self.wait_image(folder_id)
        self.assertIn("%23", ready["file_path"])
        first_path = ready["thumbnail_path"]
        first_count = len(list((self.root / "cache" / "thumbnails").rglob("*.jpg")))
        scan = self.post("/api/scan")
        self.assertEqual(self.wait_scan(scan["run_id"])["status"], "completed")
        self.assertEqual(self.wait_image(folder_id)["thumbnail_path"], first_path)
        self.assertEqual(len(list((self.root / "cache" / "thumbnails").rglob("*.jpg"))), first_count)

    def test_modify_move_and_cache_cleanup(self):
        original = self.album / "one.jpg"
        Image.new("RGB", (80, 80), "red").save(original)
        self.start_server()
        folder_id = self.folder_id()
        old_path = self.wait_image(folder_id)["thumbnail_path"]
        Image.new("RGB", (100, 100), "blue").save(original)
        updated = self.wait_image(folder_id)
        self.assertNotEqual(updated["thumbnail_path"], old_path)
        destination = self.images / "moved"
        destination.mkdir()
        original.rename(destination / "one.jpg")
        moved_id = self.folder_id("moved")
        self.assertEqual(self.get(f"/api/folders/{folder_id}/images")["total"], 0)
        self.assertEqual(self.wait_image(moved_id)["thumbnail_status"], "ready")

        orphan = self.root / "cache" / "thumbnails" / "orphan_deadbeef_thumb.jpg"
        orphan.write_bytes(b"old generated thumbnail")
        old_time = time.time() - 40 * 86400
        os.utime(orphan, (old_time, old_time))
        report = self.get("/api/cache/report")
        self.assertGreaterEqual(report["eligible_files"], 1)
        subprocess.run(
            [sys.executable, "-m", "app.services.cache_maintenance", "apply"],
            cwd=BACKEND, env=self.env, check=True, capture_output=True, text=True,
        )
        self.assertFalse(orphan.exists())
        self.assertTrue((destination / "one.jpg").exists())
        active_relative = self.wait_image(moved_id)["thumbnail_path"].removeprefix("/data/thumbnails/")
        self.assertTrue((self.root / "cache" / "thumbnails" / active_relative).is_file())

    def test_legacy_schema_keeps_existing_thumbnail(self):
        Image.new("RGB", (80, 80), "red").save(self.album / "old.jpg")
        old_thumb = self.root / "cache" / "thumbnails" / "album" / "old_deadbeef_thumb.jpg"
        old_thumb.parent.mkdir(parents=True)
        Image.new("RGB", (30, 30), "red").save(old_thumb)
        connection = sqlite3.connect(self.root / "images.db")
        connection.executescript("""
            CREATE TABLE folders (id INTEGER PRIMARY KEY, folder_path VARCHAR(512) UNIQUE,
                name VARCHAR(255), parent_id INTEGER, created_at TIMESTAMP, updated_at TIMESTAMP);
            CREATE TABLE images (id INTEGER PRIMARY KEY, folder_id INTEGER, file_path VARCHAR(512) UNIQUE,
                thumbnail_path VARCHAR(512), converted_path VARCHAR(512), mime_type VARCHAR(64),
                image_type VARCHAR(32), is_heic BOOLEAN, exif_data JSON,
                created_at TIMESTAMP, updated_at TIMESTAMP);
            INSERT INTO folders(id, folder_path, name) VALUES (1, '.', 'root');
            INSERT INTO folders(id, folder_path, name, parent_id) VALUES (2, 'album', 'album', 1);
            INSERT INTO images(id, folder_id, file_path, thumbnail_path, mime_type, image_type, is_heic)
                VALUES (1, 2, 'album/old.jpg', 'album/old_deadbeef_thumb.jpg', 'image/jpeg', 'jpeg', 0);
        """)
        connection.commit()
        connection.close()
        self.start_server()
        image = self.wait_image(2)
        self.assertEqual(image["id"], 1)
        self.assertEqual(image["thumbnail_path"], "/data/thumbnails/album/old_deadbeef_thumb.jpg")

    def test_missing_media_root_preserves_index(self):
        Image.new("RGB", (80, 80), "red").save(self.album / "one.jpg")
        self.start_server()
        folder_id = self.folder_id()
        self.wait_image(folder_id)
        self.images.rename(self.root / "offline-images")
        result = self.get("/api/folders/1/subfolders")
        self.assertEqual(result["total"], 1)
        self.assertIsNotNone(result["scan_error"])
        self.images.mkdir()
        result = self.get("/api/folders/1/subfolders")
        self.assertEqual(result["total"], 1)
        self.assertIsNotNone(result["scan_error"])

    def test_moving_folder_reindexes_subtree(self):
        nested = self.album / "nested"
        nested.mkdir()
        Image.new("RGB", (80, 80), "red").save(nested / "one.jpg")
        self.start_server()
        album_id = self.folder_id()
        nested_id = self.get(f"/api/folders/{album_id}/subfolders")["items"][0]["id"]
        self.wait_image(nested_id)
        self.album.rename(self.images / "renamed")
        renamed_id = self.folder_id("renamed")
        visible = self.get("/api/folders/1/subfolders")["items"]
        self.assertEqual([folder["name"] for folder in visible], ["renamed"])
        new_nested = self.get(f"/api/folders/{renamed_id}/subfolders")["items"][0]["id"]
        self.assertEqual(self.wait_image(new_nested)["thumbnail_status"], "ready")

    def test_broken_image_is_not_retried_on_every_visit(self):
        (self.album / "broken.jpg").write_bytes(b"not a jpeg")
        self.start_server()
        folder_id = self.folder_id()
        self.wait_image(folder_id, status="failed")
        for _ in range(3):
            image = self.get(f"/api/folders/{folder_id}/images")["items"][0]
            self.assertEqual(image["thumbnail_status"], "failed")
        with sqlite3.connect(self.root / "images.db") as connection:
            attempts = connection.execute(
                "SELECT thumbnail_attempts FROM images WHERE file_path='album/broken.jpg'"
            ).fetchone()[0]
        self.assertEqual(attempts, 1)


if __name__ == "__main__":
    unittest.main()
