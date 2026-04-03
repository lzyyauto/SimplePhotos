import { AnimatePresence, motion } from 'framer-motion';
import { useToastStore } from '../../stores/toastStore';
import { FaCheckCircle, FaExclamationCircle, FaInfoCircle, FaTimes } from 'react-icons/fa';

export const Toast = () => {
  const { toasts, removeToast } = useToastStore();

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 w-full max-w-sm px-4 md:px-0 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
            className={`pointer-events-auto flex items-start p-4 rounded-2xl shadow-lg border backdrop-blur-md text-sm ${
              toast.type === 'success'
                ? 'bg-green-50/90 border-green-200 text-green-900 dark:bg-green-900/80 dark:border-green-800/80 dark:text-green-50'
                : toast.type === 'error'
                ? 'bg-red-50/90 border-red-200 text-red-900 dark:bg-red-900/80 dark:border-red-800/80 dark:text-red-50'
                : 'bg-white/90 border-gray-200 text-gray-900 dark:bg-gray-800/90 dark:border-white/10 dark:text-gray-100'
            }`}
          >
            <div className="flex-shrink-0 mr-3 mt-0.5">
              {toast.type === 'success' && <FaCheckCircle className="w-5 h-5 text-green-500 dark:text-green-400" />}
              {toast.type === 'error' && <FaExclamationCircle className="w-5 h-5 text-red-500 dark:text-red-400" />}
              {toast.type === 'info' && <FaInfoCircle className="w-5 h-5 text-blue-500 dark:text-blue-400" />}
            </div>
            <div className="flex-1 whitespace-pre-wrap leading-relaxed">{toast.message}</div>
            <button
              onClick={() => removeToast(toast.id)}
              className="flex-shrink-0 ml-4 opacity-50 hover:opacity-100 transition-opacity focus:outline-none"
            >
              <FaTimes className="w-4 h-4" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};
