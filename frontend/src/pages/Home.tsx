import { useState, useEffect } from 'react';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
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
import { useInView } from 'react-intersection-observer';

export const Home = () => {
  const navigate = useNavigate();
  const [selectedImage, setSelectedImage] = useState<Image | null>(null);
  const { title } = useSettingsStore();
  
  // 文件夹底部观察器
  const { ref: foldersEndRef, inView: foldersEndVisible } = useInView({
    threshold: 0,
    rootMargin: '300px',
    onChange: (inView) => {
      console.log('Home folders observer:', { 
        inView, 
        hasMoreFolders, 
        isFetchingFolders,
        currentItems: allFolders.length,
        totalItems: foldersData?.pages[0]?.total
      });
    }
  });

  // 无限加载文件夹
  const {
    data: foldersData,
    fetchNextPage: fetchNextFolders,
    hasNextPage: hasMoreFolders,
    isFetchingNextPage: isFetchingFolders
  } = useInfiniteQuery({
    queryKey: ['home-folders'],
    queryFn: async ({ pageParam = 1 }) => {
      console.log('Fetching home folders page:', pageParam);
      const data = await api.getFolders(1, pageParam);
      console.log('Home folders response:', data);
      return data;
    },
    getNextPageParam: (lastPage) => {
      const nextPage = lastPage.page < lastPage.total_pages ? lastPage.page + 1 : undefined;
      console.log('Next home folders page:', nextPage);
      return nextPage;
    },
    initialPageParam: 1,
  });

  // 监听文件夹底部
  useEffect(() => {
    console.log('Home folders effect triggered:', {
      foldersEndVisible,
      hasMoreFolders,
      isFetchingFolders,
      currentPage: foldersData?.pages?.length
    });

    if (foldersEndVisible && hasMoreFolders && !isFetchingFolders) {
      console.log('Loading more home folders...');
      fetchNextFolders();
    }
  }, [foldersEndVisible, hasMoreFolders, isFetchingFolders]);

  // 合并所有文件夹��据
  const allFolders = foldersData?.pages?.flatMap(page => page?.items || []) ?? [];

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto hide-scrollbar">
      <div className="p-4">
        <h1 className="text-2xl font-bold mb-6">{title}</h1>
        
        {/* 文件夹网格 */}
        {allFolders.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold mb-4">文件夹 ({allFolders.length})</h2>
            <FolderGrid
              folders={allFolders}
              onFolderClick={(folder) => navigate(`/folder/${folder.id}`)}
            />
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

        {/* 图片查看器 */}
        <ImageViewer
          image={selectedImage}
          images={[]}
          onClose={() => setSelectedImage(null)}
          onNavigate={() => {}}
        />
      </div>
    </div>
  );
}; 