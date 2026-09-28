# SimplePhotos - Simple Photo Hub

[中文](README_zh.md)

A web application for browsing and managing your photos and videos organized in a folder structure. Powered by a Python (FastAPI) backend and a React (TypeScript, Vite) frontend.

This project was initially created as a personal solution for managing my photos through a folder-based structure. It also served as an interesting experiment in AI-assisted programming, where AI tools handled a significant portion of the coding, allowing me to focus on product design, workflow, and final adjustments.

![SimplePhotos](SimplePhotos.png)

## Key Features

- **Folder Browsing**: Easily navigate and view your photo and video folders.
- **Multimedia Support**: Supports common image and video formats.
- **Quick Preview**: Instantly display images; videos show their first frame.
- **Easy Access**: Simple API endpoints for convenient frontend access.

## Tech Stack

- **Backend**: Python, FastAPI, PostgreSQL/SQLite, SQLAlchemy, Pillow, pillow-heif
- **Frontend**: React (TypeScript), Vite

## Quick Start

```yaml
services:
  simplephotos:
    image: lzyyauto/simplephotos:latest
    ports:
      - "8000:8000"
    volumes:
      - /path/to/your/app-data:/app/data
      - /path/to/your/photos:/app/data/images:ro
    environment:
      - NODE_ENV=production
      - LANG=zh_CN.UTF-8
      - LC_ALL=zh_CN.UTF-8
      - DATA_ROOT=/app/data
      - THUMBNAIL_WORKERS=1
      - BACKGROUND_SCAN_SECONDS=21600
      - CACHE_GC_ENABLED=false
      - CACHE_GC_MIN_AGE_DAYS=30

volumes:
  data:
    driver: local
```

Pushing a `vX.Y.Z` release tag publishes one multi-platform Docker Hub image for `linux/amd64` and `linux/arm64`. Stable versions also update `latest`; Docker selects the matching image for the host. Verify the published manifest with `docker buildx imagetools inspect lzyyauto/simplephotos:latest`.

## Future Outlook

- No immediate plans for future development.

## Contribution

Contributions are welcome, including code, issues, and suggestions.
