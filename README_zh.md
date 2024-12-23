# SimplePhotos 全栈应用

## 项目概览

本项目是一个全栈 Web 应用程序，旨在处理和浏览以文件夹结构组织的图像和视频。它采用 Python 构建的后端服务 (使用 FastAPI) 和使用 TypeScript 及 Vite 开发的 React 前端。后端负责处理多媒体文件的处理、存储，并提供数据接口；前端则提供了一个用户友好的界面，用于管理和浏览按目录级别组织的多媒体内容。

## 技术栈

### 后端

- **编程语言**: Python
- **Web 框架**: FastAPI
- **数据库**: SQLite
- **数据库交互**: SQLAlchemy
- **图像处理**: Pillow, pyheif
- **其他工具**: ExifRead

### 前端

- **库 / 框架**: React
- **语言**: TypeScript
- **构建工具**: Vite

## 支持的多媒体格式

- **图像**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.heic`, `.heif`
- **视频**: `.mp4` (提取第一帧用于预览)

## 快速上手

按照以下步骤在本地机器上启动并运行应用程序。

### 后端设置

1. **导航到后端目录:**

   ```bash
   cd [项目目录]  # 如果需要，替换为实际项目目录
   ```

2. **创建并激活虚拟环境 (推荐):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # 在 Linux 或 macOS 上
   venv\Scripts\activate  # 在 Windows 上
   ```

3. **安装后端依赖:**

   ```bash
   pip install -r requirements.txt
   ```

4. **运行后端服务:**

   ```bash
   uvicorn main:app --reload
   ```

   后端服务将在 `http://localhost:8000` 上运行。

### 前端设置

1. **导航到前端目录:**

   由于 README 中提到了组合结构，请确保您位于项目根目录或指定的前端子目录中。如果前端代码不在后端目录中，请相应地调整路径。

   ```bash
   # 假设你的前端位于项目根目录下的 'frontend' 目录中
   cd frontend
   ```

2. **安装前端依赖:**

   ```bash
   npm install  # 或 yarn install 或 pnpm install
   ```

3. **运行前端开发服务器:**

   ```bash
   npm run dev   # 或 yarn dev 或 pnpm dev
   ```

   前端应用程序通常会在 `http://localhost:5173` (或控制台输出中指示的类似端口) 上运行。

## API 接口 (后端)

后端提供以下 API 接口：

### 文件夹

- **获取文件夹列表**: `GET /api/folders`
- **获取文件夹中的图像和视频**: `GET /api/folders/{folder_id}/images`
- **获取文件夹的子文件夹**: `GET /api/folders/{parent_id}/subfolders`

### 图像/视频

- **获取图像/视频详情**: `GET /api/images/{image_id}`
- **获取完整图像/视频**: `GET /api/images/{image_id}/full`

### 管理

- **触发完整扫描**: `POST /api/scan`

## 未来扩展

- 用户认证和授权
- 更多语言支持
- 高级搜索和过滤
- 图像/视频编辑功能
- 在线视频播放

## 本地化

此 README 的英文版本可在此处找到: [English Version](README.md)