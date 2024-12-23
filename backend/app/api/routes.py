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
async def get_folder_images(folder_id: int = 1,
                            page: int = Query(default=1, ge=1),
                            db: Session = Depends(get_db)):
    """获取指定文件夹中的所有图片"""
    # 使用 join 一次性获取原图和对应的缩略图
    images_query = (
        db.query(Image)  # 查询完整的 Image 对象
        .filter(Image.folder_id == folder_id, Image.image_type == 'original'))

    # 获取总数和分页
    total_images = images_query.count()
    total_pages = ceil(total_images / settings.PAGE_SIZE)

    # 获取当前页数据
    images = images_query.offset(
        (page - 1) * settings.PAGE_SIZE).limit(settings.PAGE_SIZE).all()

    # 处理路径
    def process_paths(image: Image):
        # 创建新的字典来存储处理后的数据
        image_dict = image.__dict__

        # 替换文件路径为相对路径
        if image_dict.get('file_path'):
            image_dict['file_path'] = image_dict['file_path'].replace(
                str(settings.IMAGES_DIR), '/data/images')
        if image_dict.get('thumbnail_path'):
            image_dict['thumbnail_path'] = image_dict[
                'thumbnail_path'].replace(str(settings.THUMBNAIL_DIR),
                                          '/data/thumbnails')
        if image_dict.get('converted_path'):
            image_dict['converted_path'] = image_dict[
                'converted_path'].replace(str(settings.CONVERTED_DIR),
                                          '/data/converted')

        # 移除 SQLAlchemy 的内部属性
        image_dict.pop('_sa_instance_state', None)

        return image_dict

    result = [process_paths(image) for image in images]

    return {
        "items": result,
        "total": total_images,
        "page": page,
        "total_pages": total_pages,
        "page_size": settings.PAGE_SIZE
    }


@router.get("/images/{image_id}", response_model=schemas.Image)
async def get_image(image_id: int, db: Session = Depends(get_db)):
    """获取片详细信息"""
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


@router.get("/folders/{parent_id}/subfolders")
async def get_subfolders(parent_id: int | None = None,
                         page: int = Query(default=1, ge=1),
                         db: Session = Depends(get_db)):
    """获取指定文件夹下的所有子文件夹（分页）"""
    # 构建基础查询
    if parent_id == 0:  # 约定 0 为根目录
        base_query = db.query(Folder).filter(Folder.parent_id.is_(None))
    else:
        base_query = db.query(Folder).filter(Folder.parent_id == parent_id)

    # 获取总数
    total_folders = base_query.count()
    total_pages = ceil(total_folders / settings.PAGE_SIZE)

    # 获取当前页的文件夹
    folders = base_query.offset(
        (page - 1) * settings.PAGE_SIZE).limit(settings.PAGE_SIZE).all()

    return {
        "items": folders,
        "total": total_folders,
        "page": page,
        "total_pages": total_pages,
        "page_size": settings.PAGE_SIZE
    }
