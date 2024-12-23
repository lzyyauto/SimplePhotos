# SimplePhotos Backend Service

[中文文档](README_zh.md)

## Project Overview

This project aims to develop a Python-based backend service for processing and browsing images and videos organized in a folder structure. It follows a front-end/back-end separated architecture, with the backend responsible for handling, storing, and providing data interfaces for multimedia files. This service is specifically designed for multimedia content organized by folder structure, allowing users to manage and browse through directory levels.

## Tech Stack

- **Programming Language**: Python
- **Web Framework**: FastAPI
- **Database**: SQLite
- **Database Interaction**: SQLAlchemy
- **Image Processing**: Pillow, pyheif
- **Other Tools**: ExifRead

## Supported Multimedia Formats

- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.heic`, `.heif`
- **Videos**: `.mp4` (first frame extracted for preview)

## Getting Started

1. **Clone the Repository**

   ```bash
   git clone [your_repository_address]
   cd [project_directory]
   ```

2. **Create and Activate a Virtual Environment (Recommended)**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux or macOS
   venv\Scripts\activate  # On Windows
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Service**

   ```bash
   uvicorn main:app --reload
   ```

   The service will be running at `http://localhost:8000`.

## API Endpoints

### Folders

- **Get Folder List**: `GET /api/folders`
- **Get Images and Videos in a Folder**: `GET /api/folders/{folder_id}/images`
- **Get Subfolders of a Folder**: `GET /api/folders/{parent_id}/subfolders`

### Images/Videos

- **Get Image/Video Details**: `GET /api/images/{image_id}`
- **Get Full Image/Video**: `GET /api/images/{image_id}/full`

### Management

- **Trigger Full Scan**: `POST /api/scan`

## Project Structure

```
├── PronjectInfo.md
├── __init__.py
├── app
│   ├── api
│   │   ├── routes.py       # API route definitions
│   │   └── schemas.py      # Pydantic data models
│   ├── config.py          # Project configuration
│   ├── database
│   │   ├── database.py    # Database connection and session management
│   │   └── models.py      # SQLAlchemy database models
│   ├── services
│   │   ├── cache_service.py # Cache service
│   │   ├── file_service.py  # File operation service
│   │   ├── image_service.py # Image/video processing service
│   │   └── init_service.py  # Initialization service
│   └── utils
│       ├── image_utils.py # Image processing utilities
│       └── logger.py      # Logging
├── logs
│   └── app.log           # Application logs
├── main.py               # Application entry point
├── project_structure
└── requirements.txt      # Dependency list
```

## Future Extensions

- User Authentication and Authorization
- More Language Support
- Advanced Search and Filtering
- Image/Video Editing Features
- Online Video Playback