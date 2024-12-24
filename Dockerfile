# 基础镜像
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 和必要的构建工具，添加中文支持
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libheif-dev \
    libopencv-dev \
    pkg-config \
    build-essential \
    locales

# 设置中文支持
RUN rm -rf /var/lib/apt/lists/* && \
    sed -i '/zh_CN.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen

# 设置环境变量
ENV LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN:zh \
    LC_ALL=zh_CN.UTF-8

WORKDIR /app

# 设置 Python 虚拟环境
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装后端依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装前端依赖
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install && npm install -D @types/node

# 复制前后端代码
COPY backend .
COPY frontend ./frontend

# 创建数据目录
RUN mkdir -p data/images data/cache/thumbnails data/cache/converted && \
    chown -R node:node /app

# 创建启动脚本
RUN echo '#!/bin/bash\nuvicorn main:app --host 0.0.0.0 --port 8000 &\ncd frontend && npm run dev -- --host 0.0.0.0 &\nwait' > /app/start.sh && \
    chmod +x /app/start.sh

# 暴露前端端口
EXPOSE 5173

CMD ["/app/start.sh"] 