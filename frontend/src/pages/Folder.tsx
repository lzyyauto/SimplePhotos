import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { Folder as FolderType, Image } from '@/types';
import { FolderCard } from '@/components/Gallery/FolderCard';
import { ImageGrid } from '@/components/Gallery/ImageGrid';
import { ImageViewer } from '@/components/Gallery/ImageViewer';
import { Spinner } from '@/components/Loading/Spinner';
import { Pagination } from '@/components/UI/Pagination';

export const Folder = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [selectedImage, setSelectedImage] = useState<Image | null>(null);

  const folderId = Number(id);

  // 获取子文件夹
  const { data: foldersData, isLoading: foldersLoading } = useQuery({
    queryKey: ['folders', folderId, page],
    queryFn: () => api.getFolders(folderId, page),
    enabled: !!folderId
  });

  // 只有当文件夹不足一页时才获取图片
  const shouldFetchImages = foldersData && foldersData.items.length < 50;

  // ��取当前文件夹的图片
  const { data: imagesData, isLoading: imagesLoading } = useQuery({
    queryKey: ['folder-images', folderId, page],
    queryFn: () => api.getFolderImages(folderId, page),
    enabled: !!folderId && shouldFetchImages
  });

  const handleFolderClick = (folder: FolderType) => {
    navigate(`/folder/${folder.id}`);
    setPage(1); // 重置页码
  };

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
        newIndex = settings.PAGE_SIZE - 1;
      }
    }

    // 在当前页内导航
    if (newIndex >= 0 && newIndex < imagesData.items.length) {
      setSelectedImage(imagesData.items[newIndex]);
    }
  };

  if (foldersLoading) return <Spinner />;

  return (
    <div className="p-4">
      {/* 返回按钮 */}
      <button
        onClick={() => navigate(-1)}
        className="mb-4 flex items-center text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
      >
        <svg
          className="w-5 h-5 mr-1"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        返回上级
      </button>

      {/* 文件夹网格 */}
      {foldersData?.items.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">文件夹</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {foldersData.items.map((folder) => (
              <FolderCard
                key={folder.id}
                folder={folder}
                onClick={handleFolderClick}
              />
            ))}
          </div>
          {foldersData.total_pages > 1 && (
            <Pagination
              currentPage={page}
              totalPages={foldersData.total_pages}
              onPageChange={setPage}
            />
          )}
        </div>
      )}

      {/* 图片网格 - 只在文件夹不足一页时显示 */}
      {shouldFetchImages && imagesData?.items.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">图片</h2>
          <ImageGrid
            images={imagesData.items}
            onImageClick={setSelectedImage}
          />
          {imagesData.total_pages > 1 && (
            <Pagination
              currentPage={page}
              totalPages={imagesData.total_pages}
              onPageChange={setPage}
            />
          )}
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