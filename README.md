# SimplePhotos Full-Stack Application

## Project Overview

This project is a full-stack web application designed for processing and browsing images and videos organized in a folder structure. It features a Python-based backend service built with FastAPI and a React frontend developed with TypeScript and Vite. The backend handles multimedia file processing, storage, and provides data interfaces, while the frontend offers a user-friendly interface for managing and browsing multimedia content organized by directory levels.

## Tech Stack

### Backend

- **Programming Language**: Python
- **Web Framework**: FastAPI
- **Database**: SQLite
- **Database Interaction**: SQLAlchemy
- **Image Processing**: Pillow, pyheif
- **Other Tools**: ExifRead

### Frontend

- **Library / Framework**: React
- **Language**: TypeScript
- **Build Tool**: Vite

## Supported Multimedia Formats

- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.heic`, `.heif`
- **Videos**: `.mp4` (first frame extracted for preview)

## Getting Started

Follow these steps to get the application up and running on your local machine.

### Backend Setup

1. **Navigate to the Backend Directory:**

   ```bash
   cd [project_directory]  # Replace with the actual project directory if necessary
   ```

2. **Create and Activate a Virtual Environment (Recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux or macOS
   venv\Scripts\activate  # On Windows
   ```

3. **Install Backend Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Backend Service:**

   ```bash
   uvicorn main:app --reload
   ```

   The backend service will be running at `http://localhost:8000`.

### Frontend Setup

1. **Navigate to the Frontend Directory:**

   Since the README mentions a combined structure, ensure you are in the root of your project or a designated frontend subdirectory. If the frontend code is not within the backend directory, adjust the path accordingly.

   ```bash
   # Assuming your frontend is in a 'frontend' directory at the project root
   cd frontend
   ```

2. **Install Frontend Dependencies:**

   ```bash
   npm install  # or yarn install or pnpm install
   ```

3. **Run the Frontend Development Server:**

   ```bash
   npm run dev   # or yarn dev or pnpm dev
   ```

   The frontend application will typically be running at `http://localhost:5173` (or a similar port indicated in the console output).

## API Endpoints (Backend)

The backend provides the following API endpoints:

### Folders

- **Get Folder List**: `GET /api/folders`
- **Get Images and Videos in a Folder**: `GET /api/folders/{folder_id}/images`
- **Get Subfolders of a Folder**: `GET /api/folders/{parent_id}/subfolders`

### Images/Videos

- **Get Image/Video Details**: `GET /api/images/{image_id}`
- **Get Full Image/Video**: `GET /api/images/{image_id}/full`

### Management

- **Trigger Full Scan**: `POST /api/scan`

## Future Extensions

- User Authentication and Authorization
- More Language Support
- Advanced Search and Filtering
- Image/Video Editing Features
- Online Video Playback

## Localization

A Chinese version of this README is available: [中文文档](README_zh.md)