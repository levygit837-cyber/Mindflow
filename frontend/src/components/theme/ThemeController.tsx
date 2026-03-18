import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { flushSync } from 'react-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { useAppStore } from '../../stores/appStore';
import {
  ThemeControllerContext,
  type ThemeControllerContextValue,
  type ThemeMode,
} from './themeControllerContext';

interface ThemeOrigin {
  x: number;
  y: number;
}

interface ThemeTransitionState {
  origin: ThemeOrigin;
  radius: number;
  targetTheme: ThemeMode;
}

const TRANSITION_DURATION_MS = 620;
const THEME_COMMIT_DELAY_MS = 48;
const FONT_SIZE_PRESETS = {
  small: { base: '16px', scale: '1' },
  medium: { base: '18px', scale: '1.08' },
  large: { base: '19px', scale: '1.16' },
} as const;

function resolveThemeOrigin(element: HTMLElement | null): ThemeOrigin {
  if (element) {
    const rect = element.getBoundingClientRect();
    return {
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2,
    };
  }

  if (typeof window === 'undefined') {
    return { x: 0, y: 0 };
  }

  return {
    x: window.innerWidth - 56,
    y: 48,
  };
}

function maxViewportRadius(origin: ThemeOrigin): number {
  if (typeof window === 'undefined') return 0;

  const corners = [
    { x: 0, y: 0 },
    { x: window.innerWidth, y: 0 },
    { x: 0, y: window.innerHeight },
    { x: window.innerWidth, y: window.innerHeight },
  ];

  const distances = corners.map((corner) =>
    Math.hypot(corner.x - origin.x, corner.y - origin.y),
  );

  return Math.max(...distances) + 48;
}

export const ThemeController: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const theme = useAppStore((state) => state.theme);
  const fontSize = useAppStore((state) => state.settings.fontSize);
  const setTheme = useAppStore((state) => state.setTheme);
  const reduceMotion = useReducedMotion();
  const [transition, setTransition] = useState<ThemeTransitionState | null>(null);
  const [isViewTransitioning, setIsViewTransitioning] = useState(false);
  const commitTimeoutRef = useRef<number | null>(null);
  const cleanupTimeoutRef = useRef<number | null>(null);

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  useLayoutEffect(() => {
    const preset = FONT_SIZE_PRESETS[fontSize] ?? FONT_SIZE_PRESETS.large;
    document.documentElement.dataset.fontSize = fontSize;
    document.documentElement.style.setProperty('--base-font-size', preset.base);
    document.documentElement.style.setProperty('--font-scale', preset.scale);
  }, [fontSize]);

  useEffect(() => {
    const root = document.documentElement;

    if (transition || isViewTransitioning) {
      root.classList.add('theme-transitioning');
      return () => root.classList.remove('theme-transitioning');
    }

    root.classList.remove('theme-transitioning');
    return undefined;
  }, [isViewTransitioning, transition]);

  useEffect(() => {
    return () => {
      if (commitTimeoutRef.current) {
        window.clearTimeout(commitTimeoutRef.current);
      }
      if (cleanupTimeoutRef.current) {
        window.clearTimeout(cleanupTimeoutRef.current);
      }
    };
  }, []);

  const toggleThemeFromElement = useCallback(
    (element: HTMLElement | null) => {
      const nextTheme: ThemeMode = theme === 'dark' ? 'light' : 'dark';

      if (reduceMotion) {
        setTheme(nextTheme);
        return;
      }

      const origin = resolveThemeOrigin(element);
      const radius = maxViewportRadius(origin);
      const root = document.documentElement;

      root.style.setProperty('--theme-origin-x', `${origin.x}px`);
      root.style.setProperty('--theme-origin-y', `${origin.y}px`);
      root.style.setProperty('--theme-reveal-radius', `${radius}px`);

      if (commitTimeoutRef.current) {
        window.clearTimeout(commitTimeoutRef.current);
      }
      if (cleanupTimeoutRef.current) {
        window.clearTimeout(cleanupTimeoutRef.current);
      }

      if (typeof document.startViewTransition === 'function') {
        setIsViewTransitioning(true);
        root.classList.add('theme-view-transitioning');

        const viewTransition = document.startViewTransition(() => {
          flushSync(() => setTheme(nextTheme));
        });

        viewTransition.finished.finally(() => {
          root.classList.remove('theme-view-transitioning');
          setIsViewTransitioning(false);
        });

        return;
      }

      setTransition({ origin, radius, targetTheme: nextTheme });

      commitTimeoutRef.current = window.setTimeout(() => {
        setTheme(nextTheme);
      }, THEME_COMMIT_DELAY_MS);

      cleanupTimeoutRef.current = window.setTimeout(() => {
        setTransition(null);
      }, TRANSITION_DURATION_MS + 140);
    },
    [reduceMotion, setTheme, theme],
  );

  const value = useMemo<ThemeControllerContextValue>(
    () => ({
      theme,
      isTransitioning: transition !== null || isViewTransitioning,
      toggleThemeFromElement,
    }),
    [isViewTransitioning, theme, toggleThemeFromElement, transition],
  );

  return (
    <ThemeControllerContext.Provider value={value}>
      {children}
      <AnimatePresence>
        {transition ? (
          <motion.div
            key={`${transition.targetTheme}-${transition.origin.x}-${transition.origin.y}`}
            className="theme-transition-layer"
            initial={{ opacity: 1 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
          >
            <motion.div
              className={`theme-transition-wash ${transition.targetTheme === 'light' ? 'is-light' : 'is-dark'}`}
              initial={{
                left: transition.origin.x,
                top: transition.origin.y,
                scale: 0.2,
                opacity: 0.34,
              }}
              animate={{
                left: transition.origin.x,
                top: transition.origin.y,
                scale: transition.radius / 18,
                opacity: [0.34, 0.24, 0],
              }}
              transition={{ duration: TRANSITION_DURATION_MS / 1000, ease: [0.16, 1, 0.3, 1] }}
            />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </ThemeControllerContext.Provider>
  );
};
