# SimplePhotos - 简单的图床

[English](README.md)

一个用于浏览和管理文件夹结构组织的照片和视频的 Web 应用程序。由 Python (FastAPI) 后端和 React (TypeScript, Vite) 前端驱动。

创建此项目的初衷是为自己打造一个简单直接的图片管理工具，满足我通过文件夹结构浏览的需求。同时，这也是一次有趣的 AI 编程实践，项目中大量的编码工作由各种 AI 工具完成，我专注于产品设计、流程跑通和最后的细节调整。

![SimplePhotos](SimplePhotos.png)

## 核心功能

- **文件夹浏览**:  轻松导航和查看你的照片和视频文件夹。
- **多媒体支持**: 支持常见的图像和视频格式。
- **快速预览**:  图像即时显示，视频显示首帧。
- **便捷访问**:  简单的 API 接口，方便前端调用。

## 技术栈

- **后端**: Python, FastAPI, PostgreSQL/SQLite, SQLAlchemy, Pillow, pillow-heif
- **前端**: React (TypeScript), Vite

## 快速开始

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

发布 `vX.Y.Z` 版本标签时，GitHub Actions 会将 `linux/amd64` 和 `linux/arm64` 构建为同一个多架构 Docker Hub 镜像。稳定版本也会更新 `latest`；Docker 会按服务器架构自动选择镜像。可用 `docker buildx imagetools inspect lzyyauto/simplephotos:latest` 检查发布结果。

## 索引与缩略图

首次启动只创建图库根目录记录。访问某个文件夹时，后端只读取该目录一层的文件名、大小和修改时间，然后返回文件列表；缩略图和 HEIC 转换由后台工作线程生成。页面会在处理期间自动更新缩略图，并每五分钟核对当前打开的目录。后台每隔 `BACKGROUND_SCAN_SECONDS` 秒低速核对一次目录树，不使用文件监控。设置菜单中的「深度扫描图库」可立即请求一次全库增量核对，不会清空已有索引。

`THUMBNAIL_WORKERS` 默认是 1。机械硬盘或 NAS 建议先保持这个值，确认磁盘吞吐后再调整。`FOLDER_RESCAN_SECONDS` 默认 60 秒，控制同一目录在浏览请求中再次核对的最短间隔。

## 缓存盘点与清理

在实际部署容器中先执行只读盘点：

```bash
python -m app.services.cache_maintenance report
```

报告只包含数量和字节数。确认实际缓存挂载与 PostgreSQL 索引对应后，可手动清理超过 `CACHE_GC_MIN_AGE_DAYS` 天、没有数据库引用的应用生成文件：

```bash
python -m app.services.cache_maintenance apply
```

清理范围仅限 `/app/data/cache/thumbnails` 和 `/app/data/cache/converted`，不会访问原图。如果缓存文件与数据库引用完全无法对应，清理会拒绝执行。自动清理默认关闭；完成盘点后设置 `CACHE_GC_ENABLED=true`，应用会每 24 小时运行一次同样的清理逻辑。上线前请备份 PostgreSQL 并留存缓存盘点结果。

## 未来展望

- 暂时没什么展望

## 贡献

欢迎贡献代码，提交 issue 和提出建议。
