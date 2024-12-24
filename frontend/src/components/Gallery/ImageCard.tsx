import { Image } from '@/types';
import { motion } from 'framer-motion';
import { useState } from 'react';
import { FaPlay, FaGift } from 'react-icons/fa';

interface ImageCardProps {
  image: Image;
  onClick?: (image: Image) => void;
}

export const ImageCard = ({ image, onClick }: ImageCardProps) => {
  const [isLoading, setIsLoading] = useState(true);

  const previewUrl = image.thumbnail_path || image.file_path;

  const isVideo = image.mime_type?.startsWith('video/');
  const isGif = image.mime_type === 'image/gif';

  return (
    <motion.div
      className="image-card cursor-pointer relative"
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
      
      {(isVideo || isGif) && (
        <div className="absolute bottom-2 right-2 bg-black/50 rounded-full p-2 text-white">
          {isVideo ? <FaPlay size={12} /> : <FaGift size={12} />}
        </div>
      )}
    </motion.div>
  );
}; 