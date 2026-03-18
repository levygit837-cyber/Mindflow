import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

Object.defineProperty(window, 'scrollTo', {
  value: () => {},
  writable: true,
});

// Global mock for useThemeController hook used by V2 components
// Reads theme from document.documentElement.getAttribute('data-theme')
vi.mock('../components/theme/useThemeController', () => ({
  useThemeController: () => {
    const theme = document.documentElement.getAttribute('data-theme') || 'dark';
    return {
      theme,
      setTheme: vi.fn((newTheme: string) => {
        document.documentElement.setAttribute('data-theme', newTheme);
      }),
    };
  },
}));
