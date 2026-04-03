import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useInfiniteQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { Folder as FolderType, Image } from '@/types';
import { FolderCard } from '@/components/Gallery/FolderCard';
import { ImageGrid } from '@/components/Gallery/ImageGrid';
import { ImageViewer } from '@/components/Gallery/ImageViewer';
import { Spinner } from '@/components/Loading/Spinner';
import { useInView } from 'react-intersection-observer';

export const Folder = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [selectedImage, setSelectedImage] = useState<Image | null>(null);
  
  // 文件夹底部观察器
  const { ref: foldersEndRef, inView: foldersEndVisible } = useInView({
    threshold: 0,
    rootMargin: '300px',
    onChange: (inView) => {
      console.log('Folders observer:', { 
        inView, 
        hasMoreFolders, 
        isFetchingFolders,
        currentItems: allFolders.length,
        totalItems: foldersData?.pages[0]?.total
      });
    }
  });
  // 图片底部观察器
  const { ref: imagesEndRef, inView: imagesEndVisible } = useInView({
    threshold: 0.1,
    rootMargin: '100px',
  });

  const folderId = Number(id);

  // 无限加载文件夹
  const {
    data: foldersData,
    fetchNextPage: fetchNextFolders,
    hasNextPage: hasMoreFolders,
    isFetchingNextPage: isFetchingFolders
  } = useInfiniteQuery({
    queryKey: ['folders', folderId],
    queryFn: async ({ pageParam = 1 }) => {
      console.log('Fetching folders page:', pageParam);
      const data = await api.getFolders(folderId, pageParam);
      console.log('Folders response:', data);
      return data;
    },
    getNextPageParam: (lastPage) => {
      const nextPage = lastPage.page < lastPage.total_pages ? lastPage.page + 1 : undefined;
      console.log('Next folders page:', nextPage);
      return nextPage;
    },
    initialPageParam: 1,
  });

  // 无限加载图片
  const {
    data: imagesData,
    fetchNextPage: fetchNextImages,
    hasNextPage: hasMoreImages,
    isFetchingNextPage: isFetchingImages
  } = useInfiniteQuery({
    queryKey: ['folder-images', folderId],
    queryFn: ({ pageParam = 1 }) => api.getFolderImages(folderId, pageParam),
    getNextPageParam: (lastPage) => {
      if (!lastPage || lastPage.total === 0) return undefined;
      return lastPage.page < lastPage.total_pages ? lastPage.page + 1 : undefined;
    },
    initialPageParam: 1,
  });

  // 监听文件夹底部
  useEffect(() => {
    console.log('Folders effect triggered:', {
      foldersEndVisible,
      hasMoreFolders,
      isFetchingFolders,
      currentPage: foldersData?.pages?.length
    });

    if (foldersEndVisible && hasMoreFolders && !isFetchingFolders) {
      console.log('Loading more folders...');
      fetchNextFolders().then(() => {
        console.log('Folders loaded successfully');
      }).catch(error => {
        console.error('Error loading folders:', error);
      });
    }
  }, [foldersEndVisible, hasMoreFolders, isFetchingFolders]);

  // 监听图片底部
  useEffect(() => {
    if (imagesEndVisible && hasMoreImages && !isFetchingImages) {
      console.log('Loading more images...');
      fetchNextImages();
    }
  }, [imagesEndVisible, hasMoreImages, isFetchingImages]);

  // 合并所有文件夹数据
  const allFolders = foldersData?.pages?.flatMap(page => {
    console.log('Processing page:', page);
    return page?.items || [];
  }) ?? [];
  // 合并所有图片数据
  const allImages = imagesData?.pages?.flatMap(page => page?.items || []) ?? [];

  const handleFolderClick = (folder: FolderType) => {
    navigate(`/folder/${folder.id}`);
  };

  // 处理图片导航
  const handleImageNavigation = (direction: 'prev' | 'next') => {
    if (!selectedImage) return;
    
    const currentIndex = allImages.findIndex(img => img.id === selectedImage.id);
    if (currentIndex === -1) return;

    const nextIndex = direction === 'next' ? currentIndex + 1 : currentIndex - 1;
    if (nextIndex >= 0 && nextIndex < allImages.length) {
      setSelectedImage(allImages[nextIndex]);
    }
  };

  console.log('Render state:', {
    foldersEndVisible,
    hasMoreFolders,
    isFetchingFolders,
    pagesCount: foldersData?.pages?.length,
    totalFolders: allFolders.length
  });

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto hide-scrollbar bg-gray-50/50 dark:bg-[#0B0F19] transition-colors duration-300">
      <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto pb-12">
        {/* 返回按钮 */}
        <button
          onClick={() => navigate(-1)}
          className="mb-8 flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors bg-white/50 hover:bg-white dark:bg-white/5 dark:hover:bg-white/10 px-4 py-2 rounded-xl w-fit shadow-sm border border-black/5 dark:border-white/5 backdrop-blur-sm"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </svg>
          返回
        </button>

        {/* 文件夹区域 */}
        {allFolders.length > 0 && (
          <div className="mb-10">
            <div className="flex items-center mb-5">
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">子文件夹</h2>
              <span className="text-xs font-semibold text-gray-500 bg-gray-200/60 dark:bg-gray-800 px-2.5 py-0.5 rounded-full ml-3">{allFolders.length}</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {allFolders.map((folder) => (
                <FolderCard
                  key={folder.id}
                  folder={folder}
                  onClick={handleFolderClick}
                />
              ))}
            </div>
            <div 
              ref={foldersEndRef}
              className="h-20 flex items-center justify-center mt-4 bg-gray-100/20"
            >
              {isFetchingFolders ? (
                <div className="text-center">
                  <Spinner size="sm" />
                  <div className="mt-2 text-sm text-gray-500">加载中...</div>
                </div>
              ) : hasMoreFolders ? (
                <span className="text-sm text-gray-500">
                  向下滚动加载更多 (已加载 {allFolders.length} 个)
                </span>
              ) : (
                <span className="text-sm text-gray-500">没有更多文件夹了</span>
              )}
            </div>
          </div>
        )}

        {/* 图片区域 */}
        {allImages.length > 0 && (
          <div>
            <div className="flex items-center mb-5">
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">浏览图片</h2>
            </div>
            <ImageGrid images={allImages} onImageClick={setSelectedImage} />
            <div 
              ref={imagesEndRef} 
              className="h-20 flex items-center justify-center mt-4 bg-gray-100/20"
            >
              {isFetchingImages ? (
                <Spinner size="sm" />
              ) : hasMoreImages ? (
                <span className="text-sm text-gray-500">向下滚动加载更多</span>
              ) : (
                <span className="text-sm text-gray-500">没有更多图片了</span>
              )}
            </div>
          </div>
        )}

        {/* 图片查看器 */}
        <ImageViewer
          image={selectedImage}
          images={allImages}
          onClose={() => setSelectedImage(null)}
          onNavigate={handleImageNavigation}
        />
      </div>
    </div>
  );
};