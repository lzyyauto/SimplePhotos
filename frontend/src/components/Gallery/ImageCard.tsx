import { Image } from '@/types';
import { motion } from 'framer-motion';
import { useState } from 'react';

interface ImageCardProps {
  image: Image;
  onClick?: (image: Image) => void;
}

export const ImageCard = ({ image, onClick }: ImageCardProps) => {
  const [isLoading, setIsLoading] = useState(true);

  const previewUrl = image.thumbnail_path || image.file_path;

  return (
    <motion.div
      className="image-card cursor-pointer"
      whileHover={{ scale: 1.02 }}
      onClick={() => onClick?.(image)}
    >
      {isLoading && (
        <div className="absolute inset-0 loading-skeleton" />
      )}
      <img
        src={previewUrl}
        alt=""
        className={`w-full h-full object-cover transition-opacity duration-300 ${
          isLoading ? 'opacity-0' : 'opacity-100'
        }`}
        onLoad={() => setIsLoading(false)}
      />
    </motion.div>
  );
}; 