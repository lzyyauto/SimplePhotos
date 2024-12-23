# SimplePhotos 后端服务

[English](README.md)

## 项目概述

本项目旨在开发一个基于 Python 的后端服务，用于处理和浏览文件夹结构中的图片和视频。采用前后端分离架构，后端负责多媒体文件的处理、存储和提供相关数据接口，方便用户通过目录层级进行管理和浏览。

## 技术栈

- **编程语言**: Python
- **Web 框架**: FastAPI
- **数据库**: SQLite
- **数据库交互**: SQLAlchemy
- **图片处理**: Pillow, pyheif
- **其他工具**: ExifRead

## 支持的多媒体格式

- **图片**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.heic`, `.heif`
- **视频**: `.mp4` (提取首帧作为预览图)

## 运行

1. **克隆项目仓库**

   ```bash
   git clone [你的仓库地址]
   cd [项目目录]
   ```

2. **创建并激活虚拟环境 (推荐)**

   ```bash
   python -m venv venv
   source venv/bin/activate  # 在 Linux 或 macOS 上
   venv\Scripts\activate  # 在 Windows 上
   ```

3. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

4. **运行服务**

   ```bash
   uvicorn main:app --reload
   ```

   服务将在 `http://localhost:8000` 启动。

## API 接口

### 文件夹

- **获取文件夹列表**: `GET /api/folders`
- **获取指定文件夹的图片和视频**: `GET /api/folders/{folder_id}/images`
- **获取指定文件夹的子文件夹**: `GET /api/folders/{parent_id}/subfolders`

### 图片/视频

- **获取图片/视频详细信息**: `GET /api/images/{image_id}`
- **获取完整图片/视频**: `GET /api/images/{image_id}/full`

### 管理

- **触发全盘扫描**: `POST /api/scan`

## 项目结构

```
├── PronjectInfo.md
├── __init__.py
├── app
│   ├── api
│   │   ├── routes.py       # API 路由定义
│   │   └── schemas.py      # Pydantic 数据模型
│   ├── config.py          # 项目配置
│   ├── database
│   │   ├── database.py    # 数据库连接和会话管理
│   │   └── models.py      # SQLAlchemy 数据库模型
│   ├── services
│   │   ├── cache_service.py # 缓存服务
│   │   ├── file_service.py  # 文件操作服务
│   │   ├── image_service.py # 图片/视频处理服务
│   │   └── init_service.py  # 初始化服务
│   └── utils
│       ├── image_utils.py # 图片处理工具
│       └── logger.py      # 日志记录
├── logs
│   └── app.log           # 应用日志
├── main.py               # 应用入口
├── project_structure
└── requirements.txt      # 依赖列表
```

## 未来扩展

- 用户认证与权限管理
- 更多语言支持
- 高级搜索与过滤
- 图像/视频编辑功能
- 在线视频播放