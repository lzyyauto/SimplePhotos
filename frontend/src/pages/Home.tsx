import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '@/services/api';
import { Folder, Image } from '@/types';
import { FolderCard } from '@/components/Gallery/FolderCard';
import { ImageGrid } from '@/components/Gallery/ImageGrid';
import { ImageViewer } from '@/components/Gallery/ImageViewer';
import { Spinner } from '@/components/Loading/Spinner';
import { Pagination } from '@/components/UI/Pagination';
import { useSettingsStore } from '@/stores/settingsStore';
import { FolderGrid } from '@/components/Gallery/FolderGrid';

export const Home = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [selectedImage, setSelectedImage] = useState<Image | null>(null);
  const { title, desktopColumns, mobileColumns } = useSettingsStore();
  
  // 获取文件夹列表
  const { data: foldersData, isLoading: foldersLoading } = useQuery({
    queryKey: ['folders', 1, page],
    queryFn: () => api.getFolders(1, page)
  });

  // 只有当文件夹不足一页时才获取图片
  const shouldFetchImages = foldersData && foldersData.items.length < 50;
  
  // 获取图片列表
  const { data: imagesData, isLoading: imagesLoading } = useQuery({
    queryKey: ['folder-images', 1, page],
    queryFn: () => api.getFolderImages(1, page),
    enabled: shouldFetchImages
  });

  // 处理图片导航
  const handleImageNavigation = (direction: 'prev' | 'next') => {
    if (!selectedImage || !imagesData?.items) return;
    
    const currentIndex = imagesData.items.findIndex(img => img.id === selectedImage.id);
    if (currentIndex === -1) return;

    let newIndex: number;
    if (direction === 'next') {
      newIndex = currentIndex + 1;
      // 如果是最后一张且还有下一页，加载下一页
      if (newIndex >= imagesData.items.length && page < imagesData.total_pages) {
        setPage(page + 1);
        newIndex = 0;
      }
    } else {
      newIndex = currentIndex - 1;
      // 如果是第一张且还有上一页，加载上一页
      if (newIndex < 0 && page > 1) {
        setPage(page - 1);
        newIndex = imagesData.items.length - 1;
      }
    }

    // 在当前页内导航
    if (newIndex >= 0 && newIndex < imagesData.items.length) {
      setSelectedImage(imagesData.items[newIndex]);
    }
  };

  const handleFolderClick = (folder: Folder) => {
    navigate(`/folder/${folder.id}`);
  };

  if (foldersLoading) return <Spinner />;

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-6">{title}</h1>
      
      {/* 文件夹网格 */}
      {foldersData?.items.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">文件夹</h2>
          <FolderGrid
            folders={foldersData.items}
            onFolderClick={handleFolderClick}
          />
        </div>
      )}
      
      {/* 图片网格 */}
      {shouldFetchImages && imagesData?.items.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">图片</h2>
          <ImageGrid
            images={imagesData.items}
            onImageClick={setSelectedImage}
          />
        </div>
      )}

      {/* 图片查看器 */}
      <ImageViewer
        image={selectedImage}
        images={imagesData?.items || []}
        onClose={() => setSelectedImage(null)}
        onNavigate={handleImageNavigation}
      />
    </div>
  );
}; 