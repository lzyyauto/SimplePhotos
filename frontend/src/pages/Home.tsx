import { useState, useEffect } from 'react';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '@/services/api';
import { Folder, Image } from '@/types';
import { FolderGrid } from '@/components/Gallery/FolderGrid';
import { ImageGrid } from '@/components/Gallery/ImageGrid';
import { ImageViewer } from '@/components/Gallery/ImageViewer';
import { Spinner } from '@/components/Loading/Spinner';
import { useSettingsStore } from '@/stores/settingsStore';
import { useInView } from 'react-intersection-observer';

export const Home = () => {
  const navigate = useNavigate();
  const [selectedImage, setSelectedImage] = useState<Image | null>(null);
  const { title } = useSettingsStore();
  
  // 文件夹查询
  const {
    data: foldersData,
    fetchNextPage: fetchNextFolders,
    hasNextPage: hasMoreFolders,
    isFetchingNextPage: isFetchingFolders,
    isLoading: isFoldersLoading,
  } = useInfiniteQuery({
    queryKey: ['folders', 1],
    queryFn: async ({ pageParam = 1 }) => {
      const data = await api.getFolders(1, pageParam);
      return data;
    },
    getNextPageParam: (lastPage) => 
      lastPage.page < lastPage.total_pages ? lastPage.page + 1 : undefined,
    initialPageParam: 1,
  });

  // 图片查询
  const {
    data: imagesData,
    fetchNextPage: fetchNextImages,
    hasNextPage: hasMoreImages,
    isFetchingNextPage: isFetchingImages,
    isLoading: isImagesLoading,
  } = useInfiniteQuery({
    queryKey: ['folder-images', 1],
    queryFn: async ({ pageParam = 1 }) => {
      const data = await api.getFolderImages(1, pageParam);
      return data;
    },
    getNextPageParam: (lastPage) => 
      lastPage.page < lastPage.total_pages ? lastPage.page + 1 : undefined,
    initialPageParam: 1,
  });

  // 监听滚动加载
  const { ref: foldersEndRef, inView: foldersEndVisible } = useInView({
    threshold: 0,
    rootMargin: '300px'
  });

  const { ref: imagesEndRef, inView: imagesEndVisible } = useInView({
    threshold: 0,
    rootMargin: '300px'
  });

  // 处理滚动加载
  useEffect(() => {
    if (foldersEndVisible && hasMoreFolders && !isFetchingFolders) {
      fetchNextFolders();
    }
  }, [foldersEndVisible, hasMoreFolders, isFetchingFolders]);

  useEffect(() => {
    if (imagesEndVisible && hasMoreImages && !isFetchingImages) {
      fetchNextImages();
    }
  }, [imagesEndVisible, hasMoreImages, isFetchingImages]);

  // 合并数据
  const allFolders = foldersData?.pages?.flatMap(page => page?.items || []) ?? [];
  const allImages = imagesData?.pages?.flatMap(page => page?.items || []) ?? [];

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto hide-scrollbar">
      <div className="p-4">
        <h1 className="text-2xl font-bold mb-6">{title}</h1>

        {/* 加载状态 */}
        {(isFoldersLoading || isImagesLoading) && (
          <div className="flex justify-center">
            <Spinner />
          </div>
        )}
        
        {/* 文件夹网格 */}
        {allFolders.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold mb-4">文件夹 ({allFolders.length})</h2>
            <FolderGrid
              folders={allFolders}
              onFolderClick={(folder) => navigate(`/folder/${folder.id}`)}
            />
            {/* 文件夹加载更多 */}
            <div ref={foldersEndRef} className="h-20 flex items-center justify-center">
              {isFetchingFolders && <Spinner size="sm" />}
            </div>
          </div>
        )}

        {/* 图片网格 */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">图片 ({allImages.length})</h2>
          <ImageGrid
            images={allImages}
            onImageClick={setSelectedImage}
          />
          <div ref={imagesEndRef} className="h-20 flex items-center justify-center">
            {isFetchingImages && <Spinner size="sm" />}
          </div>
        </div>

        {/* 图片查看器 */}
        <ImageViewer
          image={selectedImage}
          images={allImages}
          onClose={() => setSelectedImage(null)}
          onNavigate={(image) => setSelectedImage(image)}
        />
      </div>
    </div>
  );
}; 