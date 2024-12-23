import { Image } from '@/types';
import { ImageCard } from './ImageCard';
import { useSettingsStore } from '@/stores/settingsStore';
import { useEffect, useState } from 'react';

interface ImageGridProps {
  images: Image[];
  onImageClick: (image: Image) => void;
}

export const ImageGrid = ({ images, onImageClick }: ImageGridProps) => {
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
      {images.map((image) => (
        <ImageCard
          key={image.id}
          image={image}
          onClick={() => onImageClick(image)}
        />
      ))}
    </div>
  );
}; 