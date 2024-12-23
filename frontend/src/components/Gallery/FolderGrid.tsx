import { Folder } from '@/types';
import { FolderCard } from './FolderCard';
import { useSettingsStore } from '@/stores/settingsStore';
import { useEffect, useState } from 'react';

interface FolderGridProps {
  folders: Folder[];
  onFolderClick: (folder: Folder) => void;
}

export const FolderGrid = ({ folders, onFolderClick }: FolderGridProps) => {
  const { desktopColumns, mobileColumns } = useSettingsStore();
  const [columns, setColumns] = useState(mobileColumns);

  useEffect(() => {
    const updateColumns = () => {
      setColumns(window.innerWidth >= 768 ? desktopColumns : mobileColumns);
    };

    // 初始化
    updateColumns();

    // 监听窗口大小变化
    window.addEventListener('resize', updateColumns);
    return () => window.removeEventListener('resize', updateColumns);
  }, [desktopColumns, mobileColumns]);

  return (
    <div style={{
      display: 'grid',
      gap: '1rem',
      gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`
    }}>
      {folders.map((folder) => (
        <FolderCard
          key={folder.id}
          folder={folder}
          onClick={() => onFolderClick(folder)}
        />
      ))}
    </div>
  );
}; 