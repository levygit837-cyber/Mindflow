import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '../Sidebar/Sidebar';

export const MainLayout: React.FC = () => {
  const { pathname } = useLocation();
  const isChatPage = pathname.startsWith('/chat');

  return (
    <div className="app-shell flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {isChatPage ? (
          <Outlet />
        ) : (
          <div className="flex-1 overflow-y-auto">
            <Outlet />
          </div>
        )}
      </div>
    </div>
  );
};
