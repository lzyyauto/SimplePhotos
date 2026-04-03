import { useState, useEffect } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '@/services/api';
import { Image } from '@/types';
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
    <div className="h-[calc(100vh-4rem)] overflow-y-auto hide-scrollbar bg-gray-50/50 dark:bg-[#0B0F19] transition-colors duration-300">
      <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto pb-12">
        <h1 className="text-3xl md:text-4xl font-extrabold mb-8 text-gray-900 dark:text-white tracking-tight">{title}</h1>

        {/* 加载状态 */}
        {(isFoldersLoading || isImagesLoading) && (
          <div className="flex justify-center">
            <Spinner />
          </div>
        )}
        
        {/* 文件夹网格 */}
        {allFolders.length > 0 && (
          <div className="mb-10">
            <div className="flex items-center mb-5">
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">图库文件夹</h2>
              <span className="text-xs font-semibold text-gray-500 bg-gray-200/60 dark:bg-gray-800 px-2.5 py-0.5 rounded-full ml-3">{allFolders.length}</span>
            </div>
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
          <div className="flex items-center mb-5">
            <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">所有图片</h2>
            <span className="text-xs font-semibold text-gray-500 bg-gray-200/60 dark:bg-gray-800 px-2.5 py-0.5 rounded-full ml-3">{allImages.length}</span>
          </div>
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
          onNavigate={(direction) => {
            const currentIndex = allImages.findIndex(img => img.id === selectedImage?.id);
            if (direction === 'prev' && currentIndex > 0) {
              setSelectedImage(allImages[currentIndex - 1]);
            } else if (direction === 'next' && currentIndex < allImages.length - 1) {
              setSelectedImage(allImages[currentIndex + 1]);
            }
          }}
        />
      </div>
    </div>
  );
}; 