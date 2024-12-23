import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface SettingsState {
  title: string;
  desktopColumns: number;
  mobileColumns: number;
  setTitle: (title: string) => void;
  setDesktopColumns: (columns: number) => void;
  setMobileColumns: (columns: number) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      title: 'SimplePhotos',
      desktopColumns: 4,
      mobileColumns: 2,
      setTitle: (title) => set({ title }),
      setDesktopColumns: (columns) => set({ desktopColumns: columns }),
      setMobileColumns: (columns) => set({ mobileColumns: columns }),
    }),
    {
      name: 'settings-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
); 