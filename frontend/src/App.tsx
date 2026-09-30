import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SettingsMenu } from '@/components/UI/SettingsMenu';
import { ThemeToggle } from '@/components/UI/ThemeToggle';
import { ThumbnailProgress } from '@/components/UI/ThumbnailProgress';
import { Toast } from '@/components/UI/Toast';
import { Home } from '@/pages/Home';
import { Folder } from '@/pages/Folder';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false
    }
  }
});

const GalleryHeader = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const isFolderPage = /^\/folder\/[^/]+$/.test(location.pathname);

  const handleBack = () => {
    // Direct links have no in-app page to return to.
    if (typeof window.history.state?.idx === 'number' && window.history.state.idx > 0) {
      navigate(-1);
    } else {
      navigate('/');
    }
  };

  return (
    <div className="fixed top-0 left-0 right-0 h-16 z-40 bg-white/70 dark:bg-gray-900/70 backdrop-blur-xl border-b border-gray-200/50 dark:border-white/10 flex items-center justify-between px-4 transition-colors duration-300">
      <div>
        {isFolderPage && (
          <button
            type="button"
            onClick={handleBack}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-100 hover:text-gray-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-700 dark:text-gray-200 dark:hover:bg-white/10 dark:hover:text-white dark:focus-visible:outline-white"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
            </svg>
            返回
          </button>
        )}
      </div>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <SettingsMenu />
      </div>
    </div>
  );
};

export const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <GalleryHeader />
        
        <div className="pt-16">
          <ThumbnailProgress />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/folder/:id" element={<Folder />} />
          </Routes>
        </div>

        <Toast />
      </BrowserRouter>
    </QueryClientProvider>
  );
};
