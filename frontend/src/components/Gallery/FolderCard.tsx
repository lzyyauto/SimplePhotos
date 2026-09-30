import { Folder } from '@/types';
import { motion, useReducedMotion } from 'framer-motion';
import { useState } from 'react';

interface FolderCardProps {
  folder: Folder;
  onClick: (folder: Folder) => void;
}

export const FolderCard = ({ folder, onClick }: FolderCardProps) => {
  const [failedCover, setFailedCover] = useState<string | null>(null);
  const reduceMotion = useReducedMotion();
  const cover = folder.cover_thumbnail_path;

  return (
    <motion.button
      type="button"
      className="group h-full w-full min-w-0 rounded-2xl border border-gray-200/80 bg-white p-3 text-left shadow-sm transition-shadow duration-200 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-700 dark:border-white/10 dark:bg-gray-800/80 dark:focus-visible:outline-white"
      whileHover={reduceMotion ? undefined : { y: -2 }}
      whileTap={reduceMotion ? undefined : { scale: 0.98 }}
      onClick={() => onClick(folder)}
      title={folder.folder_path}
    >
      <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800">
        {cover && failedCover !== cover ? (
          <img
            src={cover}
            alt=""
            loading="lazy"
            decoding="async"
            onError={() => setFailedCover(cover)}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03] motion-reduce:transition-none motion-reduce:transform-none"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-gray-400 dark:text-gray-500">
            <svg
              className="h-12 w-12"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
              />
            </svg>
          </div>
        )}
      </div>
      <span className="mt-3 block min-w-0 whitespace-normal break-words px-1 pb-1 text-lg font-semibold leading-snug text-gray-900 dark:text-gray-100 [overflow-wrap:anywhere]">
        {folder.name}
      </span>
    </motion.button>
  );
};
