import { Image } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useCallback, useState, useRef } from 'react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { useSwipeable } from 'react-swipeable';

interface ImageViewerProps {
  image: Image | null;
  images: Image[];
  onClose: () => void;
  onNavigate: (direction: 'prev' | 'next') => void;
}

export const ImageViewer = ({ image, images, onClose, onNavigate }: ImageViewerProps) => {
  const [showExif, setShowExif] = useState(false);
  const [isZoomed, setIsZoomed] = useState(false);
  
  // 添加 ref 来获取 transform 实例
  const transformRef = useRef<any>(null);

  // 获取当前图片索引
  const currentIndex = image ? images.findIndex(img => img.id === image.id) : -1;
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < images.length - 1;

  // 处理导航
  const handleNavigate = (direction: 'prev' | 'next') => {
    if (isZoomed) return;
    
    if (direction === 'prev' && hasPrev) {
      onNavigate(images[currentIndex - 1]);
    } else if (direction === 'next' && hasNext) {
      onNavigate(images[currentIndex + 1]);
    }
  };

  // 滑动手势处理
  const swipeHandlers = useSwipeable({
    onSwipedLeft: () => !isZoomed && hasNext && handleNavigate('next'),
    onSwipedRight: () => !isZoomed && hasPrev && handleNavigate('prev'),
    preventDefaultTouchmoveEvent: true,
    trackMouse: false
  });

  if (!image) return null;

  const hasExif = image.exif_data && Object.keys(image.exif_data).length > 0;

  // 获取显示路径
  const displayPath = image.converted_path || image.file_path;

  // 格式化 EXIF 数据显示
  const formatExifData = (exif: any) => {
    const importantFields = {
      Make: '相机品牌',
      Model: '相机型号',
      DateTime: '拍摄时间',
      ExposureTime: '曝光时间',
      FNumber: '光圈值',
      ISO: 'ISO',
      FocalLength: '焦距',
      LensModel: '镜头型号',
    };

    return Object.entries(exif)
      .filter(([key]) => key in importantFields)
      .map(([key, value]) => ({
        label: importantFields[key as keyof typeof importantFields],
        value: value
      }));
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
        onClick={onClose}
        {...swipeHandlers}
      >
        {/* EXIF 信息按钮 */}
        {hasExif && (
          <button
            className="absolute top-4 right-4 z-50 p-2 text-white/70 hover:text-white"
            onClick={(e) => {
              e.stopPropagation();
              setShowExif(!showExif);
            }}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        )}

        {/* EXIF 信息面板 */}
        <AnimatePresence>
          {showExif && hasExif && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="absolute top-16 right-4 z-50 bg-black/80 backdrop-blur-sm rounded-lg p-4 text-white min-w-[300px]"
              onClick={e => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold mb-2">图片信息</h3>
              <div className="space-y-2">
                {formatExifData(image.exif_data).map(({ label, value }) => (
                  <div key={label} className="flex justify-between">
                    <span className="text-white/70">{label}:</span>
                    <span>{value}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 导航按钮 - 上一张 */}
        {hasPrev && (
          <button
            className="absolute left-4 p-2 text-white/70 hover:text-white z-50"
            onClick={(e) => {
              e.stopPropagation();
              handleNavigate('prev');
            }}
          >
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}

        {/* 媒体内容 */}
        <div 
          className="max-w-[90vw] max-h-[90vh] relative" 
          onClick={e => e.stopPropagation()}
        >
          {image.file_path.toLowerCase().endsWith('.mp4') ? (
            <div 
              className="relative max-w-[90vw] max-h-[90vh]" 
              onClick={e => e.stopPropagation()}
            >
              <video
                src={image.file_path}
                className="max-w-full max-h-[90vh] object-contain"
                controls
                autoPlay
                controlsList="nodownload"  // 禁用下载按钮
                playsInline  // 内联播放
                onClick={e => e.stopPropagation()}
                onMouseDown={e => e.stopPropagation()}
                onTouchStart={e => e.stopPropagation()}
                onSeeking={e => e.stopPropagation()}
                onSeeked={e => e.stopPropagation()}
              />
            </div>
          ) : (
            <TransformWrapper
              ref={transformRef}
              initialScale={1}
              minScale={0.5}
              maxScale={4}
              onZoomChange={({ state }) => {
                setIsZoomed(state.scale !== 1);
              }}
              doubleClick={{
                mode: "reset"
              }}
            >
              <TransformComponent>
                <motion.img
                  src={displayPath}
                  alt=""
                  className="max-w-full max-h-[90vh] object-contain cursor-zoom-in"
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                />
              </TransformComponent>
              
              {/* 缩放控制按钮 */}
              <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2">
                <button
                  onClick={() => transformRef.current?.zoomOut()}
                  className="p-2 rounded-full bg-black/50 text-white hover:bg-black/70"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                  </svg>
                </button>
                <button
                  onClick={() => transformRef.current?.resetTransform()}
                  className="p-2 rounded-full bg-black/50 text-white hover:bg-black/70"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v16h16" />
                  </svg>
                </button>
                <button
                  onClick={() => transformRef.current?.zoomIn()}
                  className="p-2 rounded-full bg-black/50 text-white hover:bg-black/70"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
              </div>
            </TransformWrapper>
          )}
        </div>

        {/* 导航按钮 - 下一张 */}
        {hasNext && (
          <button
            className="absolute right-4 p-2 text-white/70 hover:text-white z-50"
            onClick={(e) => {
              e.stopPropagation();
              handleNavigate('next');
            }}
          >
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}
      </motion.div>
    </AnimatePresence>
  );
}; 