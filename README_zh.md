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

- **后端**: Python, FastAPI, SQLite, SQLAlchemy, Pillow, pyheif, ExifRead
- **前端**: React (TypeScript), Vite

## 快速开始

### 后端

```bash
cd [项目目录]
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### 前端

```bash
cd frontend  # 假设前端在项目根目录的 'frontend' 目录下
npm install  # 或 yarn install / pnpm install
npm run dev   # 或 yarn dev / pnpm dev
```

## API

- **GET /api/folders**: 获取文件夹列表
- **GET /api/folders/{folder_id}/images**: 获取文件夹中的图像和视频
- **GET /api/folders/{parent_id}/subfolders**: 获取子文件夹
- **GET /api/images/{image_id}**: 获取图像/视频详情
- **GET /api/images/{image_id}/full**: 获取完整图像/视频
- **POST /api/scan**: 触发完整扫描

## 未来展望

- 暂时没什么展望

## 贡献

欢迎贡献代码，提交 issue 和提出建议。