import React from 'react';
import { motion } from 'framer-motion';
import { Brain, Menu } from 'lucide-react';
import { useAppStore } from '../../stores/appStore';
import { Button } from '../common';

export const Header: React.FC = () => {
  const theme = useAppStore((state) => state.theme);
  const setSidebarOpen = useAppStore((state) => state.setSidebarOpen);
  const setTheme = useAppStore((state) => state.setTheme);

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  return (
    <motion.header
      className="bg-surface border-b border-border px-6 py-4 flex items-center justify-between"
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="sm"
        icon={<Menu className="h-5 w-5" />}
        onClick={() => setSidebarOpen(true)}
        className="lg:hidden"
      />

      {/* Logo and title */}
      <div className="flex items-center space-x-3">
        <Brain className="h-6 w-6 text-brand-primary" />
        <div>
          <h1 className="text-lg font-semibold text-text-primary">MindFlow</h1>
          <p className="text-xs text-text-secondary">Multi-Agent AI System</p>
        </div>
      </div>

      {/* Right side actions */}
      <div className="flex items-center space-x-2">
        {/* Theme toggle */}
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleTheme}
        >
          {theme === 'dark' ? '🌙' : '☀️'}
        </Button>
      </div>
    </motion.header>
  );
};
