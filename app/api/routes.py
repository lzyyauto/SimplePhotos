from math import ceil
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api import schemas
from app.config import settings
from app.database.database import engine, get_db
from app.database.models import Folder, Image
from app.services.file_service import FileService
from app.services.image_service import ImageService
from app.services.init_service import InitializationService
from app.utils.logger import logger

router = APIRouter()


@router.get("/folders", response_model=List[schemas.Folder])
async def get_folders(db: Session = Depends(get_db)):
    """获取所有文件夹列表"""
    folders = db.query(Folder).all()
    return folders


@router.get("/folders/{folder_id}/images")
async def get_folder_images(folder_id: int,
                            page: int = Query(default=1, ge=1),
                            db: Session = Depends(get_db)):
    """获取指定文件夹中的所有图片（缩略图）"""
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # 查询该文件夹下的所有原始图片总数
    total_images = db.query(Image).filter(
        Image.folder_id == folder_id, Image.image_type == 'original').count()

    # 计算总页数
    total_pages = ceil(total_images / settings.PAGE_SIZE)

    # 获取当前页的图片
    images = db.query(Image).filter(
        Image.folder_id == folder_id, Image.image_type == 'original').offset(
            (page - 1) * settings.PAGE_SIZE).limit(settings.PAGE_SIZE).all()

    # 获取每张图片的缩略图信息
    result = []
    for image in images:
        if image.is_thumbnail:
            result.append(image)
        else:
            thumbnail = db.query(Image).filter(
                Image.parent_id == image.id,
                Image.image_type == 'thumbnail').first()
            if thumbnail:
                result.append(thumbnail)
            else:
                result.append(image)

    return {
        "items": result,
        "total": total_images,
        "page": page,
        "total_pages": total_pages,
        "page_size": settings.PAGE_SIZE
    }


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


@router.get("/")
async def root():
    return {"message": "图片浏览服务已启动"}


@router.get("/images/{image_id}/full")
async def get_image_full(image_id: int, db: Session = Depends(get_db)):
    """获取完整图片（大图预览）"""
    image = db.query(Image).filter(Image.id == image_id,
                                   Image.image_type == 'original').first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if image.is_heic and image.converted_path:
        return FileResponse(image.converted_path)
    else:
        return FileResponse(image.file_path)


@router.get("/folders/{parent_id}/subfolders",
            response_model=List[schemas.Folder])
async def get_subfolders(parent_id: int | None = None,
                         db: Session = Depends(get_db)):
    """获取指定文件夹下的所有子文件夹"""
    if parent_id == 0:  # 约定 0 为根目录
        folders = db.query(Folder).filter(Folder.parent_id.is_(None)).all()
    else:
        folders = db.query(Folder).filter(Folder.parent_id == parent_id).all()

    return folders
