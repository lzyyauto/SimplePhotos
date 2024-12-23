# SimplePhotos - Simple Photo Hub

A web application for browsing and managing your photos and videos organized in a folder structure. Powered by a Python (FastAPI) backend and a React (TypeScript, Vite) frontend.

This project was initially created as a personal solution for managing my photos through a folder-based structure. It also served as an interesting experiment in AI-assisted programming, where AI tools handled a significant portion of the coding, allowing me to focus on product design, workflow, and final adjustments.

## Key Features

- **Folder Browsing**: Easily navigate and view your photo and video folders.
- **Multimedia Support**: Supports common image and video formats.
- **Quick Preview**: Instantly display images; videos show their first frame.
- **Easy Access**: Simple API endpoints for convenient frontend access.

## Tech Stack

- **Backend**: Python, FastAPI, SQLite, SQLAlchemy, Pillow, pyheif, ExifRead
- **Frontend**: React (TypeScript), Vite

## Quick Start

### Backend

```bash
cd [project directory]
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend  # Assuming the frontend is in the 'frontend' directory at the project root
npm install  # or yarn install / pnpm install
npm run dev   # or yarn dev / pnpm dev
```

## API

- **GET /api/folders**: Get a list of folders
- **GET /api/folders/{folder_id}/images**: Get images and videos in a folder
- **GET /api/folders/{parent_id}/subfolders**: Get subfolders of a folder
- **GET /api/images/{image_id}**: Get image/video details
- **GET /api/images/{image_id}/full**: Get the full image/video
- **POST /api/scan**: Trigger a full scan

## Future Outlook

- No immediate plans for future development.

## Contribution

Contributions are welcome, including code, issues, and suggestions.