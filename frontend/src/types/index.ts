export interface Image {
  id: number;
  folder_id: number;
  is_heic: boolean;
  is_thumbnail: boolean;
  image_type: string;
  file_path: string;
  thumbnail_path: string;
  converted_path: string | null;
  exif_data?: Record<string, any>;
}

export interface Folder {
  id: number;
  name: string;
  folder_path: string;
  parent_id: number | null;
  has_subfolders: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  total_pages: number;
  page_size: number;
} 