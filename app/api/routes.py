from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import schemas
from app.database.database import engine, get_db
from app.services.file_service import FileService
from app.services.image_service import ImageService
from app.services.init_service import InitializationService
from app.utils.logger import logger

router = APIRouter()


@router.get("/folders", response_model=List[schemas.Folder])
async def get_folders(db: Session = Depends(get_db)):
    """获取所有文件夹列表"""
    folders = db.query(schemas.Folder).all()
    return folders


@router.get("/folders/{folder_id}/images", response_model=List[schemas.Image])
async def get_folder_images(folder_id: int, db: Session = Depends(get_db)):
    """获取指定文件夹中的所有图片"""
    folder = db.query(
        schemas.Folder).filter(schemas.Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    images = db.query(schemas.Image).filter(
        schemas.Image.file_path.startswith(folder.folder_path)).all()
    return images


@router.get("/images/{image_id}", response_model=schemas.Image)
async def get_image(image_id: int, db: Session = Depends(get_db)):
    """获取图片详细信息"""
    image_service = ImageService(db)
    image = await image_service.get_image(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


@router.post("/scan")
async def trigger_full_scan(db: Session = Depends(get_db)):
    """手动触发全盘扫描"""
    try:
        init_service = InitializationService(db, engine)
        folders_count, images_count = await init_service.full_scan()
        return {
            "status": "success",
            "message": "全盘扫描完成",
            "data": {
                "folders_processed": folders_count,
                "images_processed": images_count
            }
        }
    except Exception as e:
        logger.error(f"手动扫描失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/structure/{path:path}")
async def get_structure(path: str, db: Session = Depends(get_db)):
    """获取文件夹结构"""
    try:
        file_service = FileService(db)
        structure = file_service.get_folder_structure(path)
        return structure
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def root():
    return {"message": "图片浏览服务已启动"}
