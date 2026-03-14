import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '../Sidebar/Sidebar';

export const MainLayout: React.FC = () => {
  const { pathname } = useLocation();
  const isChatPage = pathname.startsWith('/chat');

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: '#080614' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {isChatPage ? (
          // Chat page manages its own layout entirely
          <Outlet />
        ) : (
          // Other pages get padding + scroll
          <div className="flex-1 overflow-y-auto p-6">
            <Outlet />
          </div>
        )}
      </div>
    </div>
  );
};
