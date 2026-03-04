import React from 'react';
import { motion } from 'framer-motion';
import { Menu, Brain, Cpu } from 'lucide-react';
import { useUIState, useAppStore } from '../../stores/appStore';
import { Button } from '../common';

export const Header: React.FC = () => {
  const { reasoningPanelOpen, theme } = useUIState();
  const { setSidebarOpen, setReasoningPanelOpen, setTheme } = useAppStore();

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
          <h1 className="text-lg font-semibold text-text-primary">OmniMind</h1>
          <p className="text-xs text-text-secondary">Multi-Agent AI System</p>
        </div>
      </div>

      {/* Right side actions */}
      <div className="flex items-center space-x-2">
        {/* Reasoning panel toggle */}
        <Button
          variant={reasoningPanelOpen ? 'primary' : 'ghost'}
          size="sm"
          icon={<Cpu className="h-4 w-4" />}
          onClick={() => setReasoningPanelOpen(!reasoningPanelOpen)}
        >
          Reasoning
        </Button>

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
