import asyncio
from math import ceil
from urllib.parse import quote

from app.config import settings
from app.database.database import get_db
from app.database.models import Folder, Image, ScanRun
from app.services.cache_maintenance import CacheMaintenance
from app.services.folder_service import FolderService
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

router = APIRouter()


def _build_image_dict(image: Image) -> dict:
    return {
        "id": image.id,
        "folder_id": image.folder_id,
        "file_path": f"/data/images/{quote(image.file_path, safe='/')}",
        "thumbnail_path": (
            f"/data/thumbnails/{quote(image.thumbnail_path, safe='/')}" if image.thumbnail_path else None
        ),
        "converted_path": (
            f"/data/converted/{quote(image.converted_path, safe='/')}" if image.converted_path else None
        ),
        "mime_type": image.mime_type,
        "image_type": image.image_type,
        "is_heic": image.is_heic,
        "exif_data": image.exif_data,
        "thumbnail_status": image.thumbnail_status,
        "thumbnail_retryable": (
            image.thumbnail_status == "failed"
            and image.thumbnail_attempts < settings.THUMBNAIL_MAX_RETRIES
        ),
        "thumbnail_error": image.thumbnail_error if image.thumbnail_status == "failed" else None,
        "created_at": image.created_at.isoformat() if image.created_at else None,
        "updated_at": image.updated_at.isoformat() if image.updated_at else None,
    }


async def _refresh_folder(folder_id: int, request: Request, priority: int = 10):
    result = await asyncio.to_thread(
        FolderService().reconcile_folder, folder_id, priority=priority
    )
    if result.scanned or result.updated or result.discovered:
        request.app.state.library_worker.wake()
    return result


@router.get("/folders")
async def get_folders(db: Session = Depends(get_db)):
    return db.query(Folder).filter(Folder.missing_since.is_(None)).all()


@router.get("/folders/{folder_id}/images")
async def get_folder_images(
    request: Request,
    folder_id: int,
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    result = await _refresh_folder(folder_id, request)
    if result.error == "目录不存在于索引中":
        raise HTTPException(status_code=404, detail=result.error)
    query = db.query(Image).filter(
        Image.folder_id == folder_id, Image.missing_since.is_(None)
    )
    count = query.count()
    images = query.order_by(Image.file_path.asc()).offset(
        (page - 1) * settings.PAGE_SIZE
    ).limit(settings.PAGE_SIZE).all()
    return {
        "items": [_build_image_dict(image) for image in images],
        "total": count,
        "page": page,
        "total_pages": ceil(count / settings.PAGE_SIZE),
        "page_size": settings.PAGE_SIZE,
        "scan_error": result.error,
    }


@router.get("/folders/{parent_id}/subfolders")
async def get_subfolders(
    request: Request,
    parent_id: int,
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    result = None if parent_id == 0 else await _refresh_folder(parent_id, request)
    if result and result.error == "目录不存在于索引中":
        raise HTTPException(status_code=404, detail=result.error)
    condition = Folder.parent_id.is_(None) if parent_id == 0 else Folder.parent_id == parent_id
    query = db.query(Folder).filter(condition, Folder.missing_since.is_(None))
    count = query.count()
    folders = query.order_by(Folder.name.asc(), Folder.id.asc()).offset(
        (page - 1) * settings.PAGE_SIZE
    ).limit(settings.PAGE_SIZE).all()
    return {
        "items": folders,
        "total": count,
        "page": page,
        "total_pages": ceil(count / settings.PAGE_SIZE),
        "page_size": settings.PAGE_SIZE,
        "scan_error": result.error if result else None,
    }


@router.get("/images/{image_id}")
async def get_image(image_id: int, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if image is None or image.missing_since is not None:
        raise HTTPException(status_code=404, detail="Image not found")
    return _build_image_dict(image)


@router.get("/images/{image_id}/full")
async def get_image_full(image_id: int, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if image is None or image.missing_since is not None:
        raise HTTPException(status_code=404, detail="Image not found")
    if image.is_heic and image.converted_path:
        full_path = settings.CONVERTED_DIR / image.converted_path
    else:
        full_path = settings.IMAGES_DIR / image.file_path
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(full_path)


@router.post("/scan")
async def trigger_full_scan(request: Request):
    run_id = request.app.state.library_worker.request_scan()
    return {"status": "pending", "run_id": run_id}


@router.get("/scan/{run_id}")
async def get_scan_status(run_id: int, db: Session = Depends(get_db)):
    run = db.get(ScanRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {
        "status": run.status,
        "run_id": run.id,
        "folders_scanned": run.folders_scanned,
        "images_discovered": run.images_discovered,
        "images_updated": run.images_updated,
        "error": run.error,
    }


@router.get("/cache/report")
async def get_cache_report():
    return await asyncio.to_thread(CacheMaintenance().run, dry_run=True)


@router.get("/")
async def root():
    return {"message": "图片浏览服务已启动"}
