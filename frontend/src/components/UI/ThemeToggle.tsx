import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export const ThemeToggle = () => {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const isDarkMode = document.documentElement.classList.contains('dark');
    setIsDark(isDarkMode);
  }, []);

  const toggleTheme = () => {
    const newIsDark = !isDark;
    setIsDark(newIsDark);
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', newIsDark ? 'dark' : 'light');
  };

  return (
    <button
      onClick={toggleTheme}
      className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors duration-300 focus:outline-none shadow-inner
        ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-gray-200 border border-gray-300'}`}
      role="switch"
      aria-checked={isDark}
      aria-label="Toggle Theme"
    >
      <motion.div
        className="absolute w-6 h-6 bg-white rounded-full shadow-sm flex items-center justify-center z-10 overflow-hidden"
        initial={false}
        animate={{
          left: isDark ? '30px' : '4px',
        }}
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      >
        <motion.svg
          className="w-3.5 h-3.5 text-gray-800"
          initial={false}
          animate={{
            rotate: isDark ? 0 : 90,
            opacity: isDark ? 1 : 0,
            scale: isDark ? 1 : 0.5,
          }}
          transition={{ duration: 0.2 }}
          viewBox="0 0 24 24"
          fill="currentColor"
          style={{ position: 'absolute' }}
        >
          <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </motion.svg>
        <motion.svg
          className="w-4 h-4 text-yellow-500"
          initial={false}
          animate={{
            rotate: isDark ? -90 : 0,
            opacity: isDark ? 0 : 1,
            scale: isDark ? 0.5 : 1,
          }}
          transition={{ duration: 0.2 }}
          viewBox="0 0 24 24"
          fill="currentColor"
          style={{ position: 'absolute' }}
        >
          <path fillRule="evenodd" d="M12 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4.22 3.364a1 1 0 011.415 0l.707.707a1 1 0 01-1.414 1.414l-.707-.707a1 1 0 010-1.414zM21 11a1 1 0 110 2h-1a1 1 0 110-2h1zm-3.364 4.22a1 1 0 010 1.415l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 0zM12 18a1 1 0 110 2v1a1 1 0 11-2 0v-1a1 1 0 112 0zm-4.22-3.364a1 1 0 01-1.415 0l-.707-.707a1 1 0 011.414-1.414l.707.707a1 1 0 010 1.414zM5 11a1 1 0 010 2H4a1 1 0 010-2h1zm3.364-4.22a1 1 0 010-1.415l.707-.707a1 1 0 011.414 1.414l-.707.707a1 1 0 01-1.414 0zM12 6a6 6 0 100 12 6 6 0 000-12z" clipRule="evenodd" />
        </motion.svg>
      </motion.div>
    </button>
  );
};