import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SettingsMenu } from '@/components/UI/SettingsMenu';
import { ThemeToggle } from '@/components/UI/ThemeToggle';
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

export const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {/* Navbar */}
        <div className="fixed top-0 left-0 right-0 h-16 z-40 bg-white/70 dark:bg-gray-900/70 backdrop-blur-xl border-b border-gray-200/50 dark:border-white/10 flex items-center justify-between px-4 transition-colors duration-300">
          <div className="font-semibold text-lg tracking-tight text-gray-900 dark:text-white"></div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <SettingsMenu />
          </div>
        </div>
        
        <div className="pt-16">
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
