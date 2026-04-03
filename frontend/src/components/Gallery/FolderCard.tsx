import { Folder } from '@/types';
import { motion } from 'framer-motion';

interface FolderCardProps {
  folder: Folder;
  onClick: (folder: Folder) => void;
}

export const FolderCard = ({ folder, onClick }: FolderCardProps) => {
  return (
    <motion.div
      className="p-5 rounded-2xl bg-white dark:bg-gray-800/80 cursor-pointer border border-gray-100 dark:border-white/5 shadow-sm hover:shadow-md transition-all duration-300 backdrop-blur-sm group"
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick(folder)}
      layout
    >
      <div className="flex items-center gap-4">
        <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gray-50 dark:bg-gray-700/50 text-gray-500 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors border border-gray-100 dark:border-gray-600/50">
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
            />
          </svg>
        </div>
        <div className="flex flex-col flex-1 min-w-0">
          <span className="font-bold text-gray-900 dark:text-gray-100 truncate text-xl">
            {folder.name}
          </span>
          <span className="text-sm text-gray-400 dark:text-gray-500 mt-1 truncate">
            {folder.folder_path}
          </span>
        </div>
        <div className="flex-shrink-0 text-gray-300 dark:text-gray-600 group-hover:text-gray-400 dark:group-hover:text-gray-400 transition-colors transform group-hover:translate-x-1 duration-300">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </motion.div>
  );
};