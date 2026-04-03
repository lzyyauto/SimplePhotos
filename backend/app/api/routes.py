import asyncio
import os
from math import ceil
from typing import List

from app.api import schemas
from app.config import settings
from app.database.database import engine, get_db
from app.database.models import Folder, Image
from app.services.file_service import FileService
from app.services.folder_service import FolderService
from app.services.image_service import ImageService
from app.services.init_service import InitializationService
from app.utils.logger import logger
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/folders", response_model=List[schemas.Folder])
async def get_folders(db: Session = Depends(get_db)):
    """获取所有文件夹列表"""
    return db.query(Folder).all()


@router.get("/folders/{folder_id}/images")
async def get_folder_images(
    folder_id: int = 1,
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    """获取指定文件夹中的所有图片（分页）"""
    images_query = db.query(Image).filter(Image.folder_id == folder_id)

    total_images = images_query.count()
    total_pages = ceil(total_images / settings.PAGE_SIZE)

    images = (
        images_query
        .offset((page - 1) * settings.PAGE_SIZE)
        .limit(settings.PAGE_SIZE)
        .all()
    )

    def build_image_dict(image: Image) -> dict:
        """将 Image ORM 对象转换为前端可用的字典，路径转换为 URL 路径"""
        return {
            "id": image.id,
            "folder_id": image.folder_id,
            "file_path": f"/data/images/{image.file_path}" if image.file_path else None,
            "thumbnail_path": f"/data/thumbnails/{image.thumbnail_path}" if image.thumbnail_path else None,
            "converted_path": f"/data/converted/{image.converted_path}" if image.converted_path else None,
            "mime_type": image.mime_type,
            "image_type": image.image_type,
            "is_heic": image.is_heic,
            "exif_data": image.exif_data,
            "created_at": image.created_at.isoformat() if image.created_at else None,
            "updated_at": image.updated_at.isoformat() if image.updated_at else None,
        }

    return {
        "items": [build_image_dict(img) for img in images],
        "total": total_images,
        "page": page,
        "total_pages": total_pages,
        "page_size": settings.PAGE_SIZE,
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
        init_service = InitializationService(db)
        success, message = await init_service.full_scan()
        if not success:
            raise HTTPException(status_code=500, detail=message)

        # 全量扫描完成后清空文件夹验证缓存
        # 让下次用户浏览时能感知到最新状态
        FolderService.clear_all_cache()

        return {"status": "success", "message": message}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动扫描失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def root():
    return {"message": "图片浏览服务已启动"}


@router.get("/images/{image_id}/full")
async def get_image_full(image_id: int, db: Session = Depends(get_db)):
    """
    获取完整图片/视频文件。
    - HEIC 文件：返回转换后的 JPEG（converted_path）
    - 其他格式：返回原文件（file_path）
    """
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # 所有路径均为相对路径，需拼接到实际目录
    if image.is_heic and image.converted_path:
        full_path = os.path.join(settings.CONVERTED_DIR, image.converted_path)
        return FileResponse(full_path)
    else:
        full_path = os.path.join(settings.IMAGES_DIR, image.file_path)
        return FileResponse(full_path)


@router.get("/folders/{parent_id}/subfolders")
async def get_subfolders(
    parent_id: int = 1,
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    """获取指定文件夹下的所有子文件夹（分页）"""
    if parent_id == 0:
        # 约定 0 为根目录（parent_id 为 NULL 的记录）
        base_query = db.query(Folder).filter(
            Folder.parent_id.is_(None)
        ).order_by(Folder.name.asc())
    else:
        base_query = db.query(Folder).filter(
            Folder.parent_id == parent_id
        ).order_by(Folder.name.asc())

    # 后台异步触发文件夹内容验证（补偿机制）
    folder_service = FolderService(db)
    asyncio.create_task(folder_service.validate_folder_content(parent_id))

    total_folders = base_query.count()
    total_pages = ceil(total_folders / settings.PAGE_SIZE)
    folders = (
        base_query
        .offset((page - 1) * settings.PAGE_SIZE)
        .limit(settings.PAGE_SIZE)
        .all()
    )

    return {
        "items": folders,
        "total": total_folders,
        "page": page,
        "total_pages": total_pages,
        "page_size": settings.PAGE_SIZE,
    }

