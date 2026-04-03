# =============================================================================
# Stage 1: 前端构建（Node.js 环境，仅用于编译，不进入最终镜像）
# =============================================================================
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend

# 先复制 package.json，利用 Docker layer 缓存
# 只要 package.json 不变，npm install 层就不会重新执行
COPY frontend/package*.json ./
RUN npm ci --prefer-offline

# 复制源码并构建
COPY frontend/ ./
RUN npm run build
# 产物在 /build/frontend/dist/


# =============================================================================
# Stage 2: Python 依赖安装（仅用于安装，不进入最终镜像）
# =============================================================================
FROM python:3.11-slim AS python-builder

# 安装编译 Python 包所需的系统依赖（pillow-heif/pyheif 需要 libheif）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libheif-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖到独立目录，便于复制到最终镜像
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# =============================================================================
# Stage 3: 最终运行镜像（只包含运行所需，不含任何构建工具）
# =============================================================================
FROM python:3.11-slim AS runtime

# ---- 系统运行时依赖（只要 runtime 库，不要 -dev 包）----
# ffmpeg:     视频首帧提取（必须）
# libheif1:   HEIC 格式运行时支持（pillow-heif 依赖）
# libsm6/libxext6/libgl1: OpenCV 运行时（opencv-python 依赖）
# locales:    中文支持
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libheif1 \
    libsm6 \
    libxext6 \
    libgl1 \
    locales \
    && sed -i '/zh_CN.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN:zh \
    LC_ALL=zh_CN.UTF-8

# ---- 从 python-builder 复制 Python 包 ----
COPY --from=python-builder /install /usr/local

# ---- 从 frontend-builder 复制编译后的静态文件 ----
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# ---- 复制后端代码 ----
WORKDIR /app
COPY backend/ .

# ---- 创建必要的数据目录 ----
RUN mkdir -p data/images data/cache/thumbnails data/cache/converted \
    && chown -R 1000:1000 /app

# 只暴露后端 API 端口（前端静态文件由 FastAPI 托管）
EXPOSE 8000

# 以非 root 用户运行（安全最佳实践）
USER 1000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]