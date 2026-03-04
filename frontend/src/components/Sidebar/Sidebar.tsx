import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Brain, 
  MessageSquare, 
  Settings, 
  X,
  Home
} from 'lucide-react';
import { useUIState, useSettings, useAppStore } from '../../stores/appStore';
import { Button } from '../common';

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { sidebarOpen } = useUIState();
  const { language } = useSettings();
  const { setSidebarOpen } = useAppStore();

  const menuItems = [
    {
      path: '/',
      icon: Home,
      label: language === 'pt' ? 'Início' : 'Dashboard',
      description: language === 'pt' ? 'Visão geral' : 'Overview',
    },
    {
      path: '/chat',
      icon: MessageSquare,
      label: language === 'pt' ? 'Chat' : 'Chat',
      description: language === 'pt' ? 'Conversar com agentes' : 'Chat with agents',
    },
    {
      path: '/settings',
      icon: Settings,
      label: language === 'pt' ? 'Configurações' : 'Settings',
      description: language === 'pt' ? 'Preferências do sistema' : 'System preferences',
    },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <motion.div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <motion.div
        className={`fixed top-0 left-0 h-full w-64 bg-surface border-r border-border z-50 transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        initial={false}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center space-x-2">
            <Brain className="h-8 w-8 text-brand-primary" />
            <span className="text-lg font-bold text-text-primary">OmniMind</span>
          </div>
          
          <Button
            variant="ghost"
            size="sm"
            icon={<X className="h-4 w-4" />}
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden"
          />
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
              >
                <motion.div
                  className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                    active
                      ? 'bg-brand-primary text-white'
                      : 'text-text-secondary hover:text-text-primary hover:bg-surface-elevated'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Icon className="h-5 w-5" />
                  <div>
                    <div className="font-medium">{item.label}</div>
                    <div className="text-xs opacity-75">{item.description}</div>
                  </div>
                </motion.div>
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border">
          <div className="text-xs text-text-disabled">
            {language === 'pt' ? 'Sistema Multi-Agentes IA' : 'Multi-Agent AI System'}
          </div>
        </div>
      </motion.div>
    </>
  );
};
