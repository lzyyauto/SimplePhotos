"""Initialize the index without decoding the entire library at startup."""

from app.config import settings
from app.database.models import Folder
from app.utils.logger import logger
from sqlalchemy.orm import Session


class InitializationService:
    def __init__(self, db: Session):
        self.db = db

    def initialize_database(self) -> bool:
        if not settings.IMAGES_DIR.is_dir():
            logger.error("图片目录不存在: %s", settings.IMAGES_DIR)
            return False
        root = self.db.query(Folder).filter(Folder.folder_path == ".").first()
        if root is None:
            self.db.add(Folder(folder_path=".", name="root", parent_id=None))
            self.db.commit()
        return True
