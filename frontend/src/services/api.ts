const API_BASE = 'http://localhost:8000/api';

export const api = {
  async getFolders(parentId: number, page: number = 1) {
    const response = await fetch(
      `${API_BASE}/folders/${parentId}/subfolders?page=${page}`
    );
    return response.json();
  },

  async getFolderImages(folderId: number, page: number = 1) {
    const response = await fetch(
      `${API_BASE}/folders/${folderId}/images?page=${page}`
    );
    return response.json();
  },

  getImageUrl(imageId: number) {
    return `${API_BASE}/images/${imageId}/full`;
  },

  post: async (endpoint: string, data?: any) => {
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