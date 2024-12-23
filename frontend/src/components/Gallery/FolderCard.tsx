import { Folder } from '@/types';
import { motion } from 'framer-motion';

interface FolderCardProps {
  folder: Folder;
  onClick: (folder: Folder) => void;
}

export const FolderCard = ({ folder, onClick }: FolderCardProps) => {
  return (
    <motion.div
      className="p-4 rounded-lg bg-gray-100 dark:bg-gray-800 cursor-pointer"
      whileHover={{ scale: 1.02 }}
      onClick={() => onClick(folder)}
    >
      <div className="flex items-center gap-3">
        <svg
          className="w-6 h-6 text-gray-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
          />
        </svg>
        <span className="font-medium truncate">{folder.name}</span>
      </div>
    </motion.div>
  );
}; 