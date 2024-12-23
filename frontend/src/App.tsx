import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SettingsMenu } from '@/components/UI/SettingsMenu';
import { ThemeToggle } from '@/components/UI/ThemeToggle';
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
        <div className="fixed top-4 right-4 z-40 flex items-center gap-2">
          <ThemeToggle />
          <SettingsMenu />
        </div>
        
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/folder/:id" element={<Folder />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};
