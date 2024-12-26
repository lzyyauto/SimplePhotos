import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  title: string;
  theme: 'light' | 'dark' | 'system';
  desktopColumns: number;
  mobileColumns: number;
  setTitle: (title: string) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setDesktopColumns: (columns: number) => void;
  setMobileColumns: (columns: number) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      title: 'SimplePhotos',
      theme: 'system',
      desktopColumns: 3,
      mobileColumns: 1,
      setTitle: (title) => set({ title }),
      setTheme: (theme) => set({ theme }),
      setDesktopColumns: (columns) => set({ desktopColumns: columns }),
      setMobileColumns: (columns) => set({ mobileColumns: columns }),
    }),
    {
      name: 'settings-storage',
    }
  )
); 