import type { Folder, Image, PaginatedResponse } from '../types';

const API_BASE = '/api';

export const api = {
  async getFolders(parentId: number, page: number = 1): Promise<PaginatedResponse<Folder>> {
    const response = await fetch(
      `${API_BASE}/folders/${parentId}/subfolders?page=${page}`
    );
    if (!response.ok) throw new Error('读取文件夹失败');
    return response.json();
  },

  async getFolderImages(folderId: number, page: number = 1): Promise<PaginatedResponse<Image>> {
    const response = await fetch(
      `${API_BASE}/folders/${folderId}/images?page=${page}`
    );
    if (!response.ok) throw new Error('读取图片失败');
    return response.json();
  },

  getImageUrl(imageId: number) {
    return `${API_BASE}/images/${imageId}/full`;
  },

  async getScanStatus(runId: number): Promise<{
    status: string; run_id: number; folders_scanned: number;
    images_discovered: number; images_updated: number; error: string | null;
  }> {
    const response = await fetch(`${API_BASE}/scan/${runId}`);
    if (!response.ok) throw new Error('读取扫描状态失败');
    return response.json();
  },

  post: async (endpoint: string, data?: unknown): Promise<{ status: string; run_id: number }> => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    
    if (!response.ok) {
      throw new Error('API request failed');
    }
    
    return response.json();
  },
};
