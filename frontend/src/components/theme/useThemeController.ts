import { useContext } from 'react';
import { ThemeControllerContext } from './themeControllerContext';

export function useThemeController() {
  const context = useContext(ThemeControllerContext);

  if (!context) {
    throw new Error('useThemeController must be used within ThemeController');
  }

  return context;
}
