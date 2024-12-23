import { useEffect, useState } from 'react';

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
      className="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none
                bg-gray-200 dark:bg-blue-600"
      role="switch"
      aria-checked={isDark}
    >
      <span className="sr-only">切换主题</span>
      <span
        className={`${
          isDark ? 'translate-x-6 bg-white' : 'translate-x-1 bg-white'
        } inline-block h-4 w-4 transform rounded-full transition-transform duration-200 ease-in-out
        flex items-center justify-center`}
      >
        {isDark ? (
          <svg className="w-3 h-3 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
            <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
        ) : (
          <svg className="w-3 h-3 text-yellow-400" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        )}
      </span>
    </button>
  );
}; 