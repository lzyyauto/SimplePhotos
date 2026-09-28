import { Image } from '@/types';
import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { FaPlay, FaGift } from 'react-icons/fa';

interface ImageCardProps {
  image: Image;
  onClick?: (image: Image) => void;
}

export const ImageCard = ({ image, onClick }: ImageCardProps) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const previewUrl = image.thumbnail_path;

  useEffect(() => {
    setIsLoading(true);
    setHasError(false);
  }, [previewUrl]);

  const isVideo = image.mime_type?.startsWith('video/');
  const isGif = image.mime_type === 'image/gif';

  return (
    <motion.div
      className="relative cursor-pointer rounded-2xl overflow-hidden group shadow-sm bg-gray-100 dark:bg-gray-800 border border-black/5 dark:border-white/5"
      whileHover={{ scale: 1.01, y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick?.(image)}
      layout
    >
      {(!previewUrl || isLoading) && (
        <div className="absolute inset-0 animate-pulse bg-gray-200 dark:bg-gray-700" />
      )}
      <div className="aspect-square w-full">
        {previewUrl && !hasError ? (
          <img
            src={previewUrl}
            alt=""
            className={`w-full h-full object-cover transition-all duration-500 ease-in-out ${
              isLoading ? 'opacity-0 scale-105' : 'opacity-100 scale-100 group-hover:scale-105'
            }`}
            onLoad={() => setIsLoading(false)}
            onError={() => { setIsLoading(false); setHasError(true); }}
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-sm text-gray-500">
            {hasError || (image.thumbnail_status === 'failed' && !image.thumbnail_retryable)
              ? '缩略图生成失败' : '缩略图处理中'}
          </div>
        )}
      </div>
      
      {/* 渐变遮罩用于 hover */}
      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors duration-300 pointer-events-none" />

      {previewUrl && image.thumbnail_status !== 'ready' && (
        <span className="absolute bottom-3 left-3 rounded-lg bg-black/50 px-2 py-1 text-xs text-white">
          缩略图更新中
        </span>
      )}

      {(isVideo || isGif) && (
        <div className="absolute top-3 right-3 bg-black/30 backdrop-blur-md rounded-xl p-2 text-white shadow-sm border border-white/20">
          {isVideo ? <FaPlay size={12} className="opacity-90" /> : <FaGift size={12} className="opacity-90" />}
        </div>
      )}
    </motion.div>
  );
};
