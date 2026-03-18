import { createContext } from 'react';

export type ThemeMode = 'light' | 'dark';

export interface ThemeControllerContextValue {
  theme: ThemeMode;
  isTransitioning: boolean;
  toggleThemeFromElement: (element: HTMLElement | null) => void;
}

export const ThemeControllerContext = createContext<ThemeControllerContextValue | null>(null);
