import React from 'react';
import { Sidebar } from './Sidebar';
import { InputBar } from '../input/InputBar';
import { ShareNetwork, Gear } from '@phosphor-icons/react';
import { AgentType } from '../../lib/constants';
import { ChatSession } from '../../types/backend';

interface ChatLayoutProps {
  children: React.ReactNode;
  sessionTitle?: string;
  folderPath?: string;
  selectedAgent?: AgentType | null;
  contextPaths?: string[];
  isOrchestrateMode?: boolean;
  sessions?: ChatSession[];
  currentSessionId?: string | null;
  isSessionsLoading?: boolean;
  onSend?: (text: string) => void | Promise<void>;
  onSelectAgent?: (agent: AgentType | null) => void;
  onToggleOrchestrate?: () => void;
  onFolderClick?: () => void;
  onNewSession?: () => void;
  onSelectSession?: (id: string) => void;
  onDeleteSession?: (id: string) => void;
  onRenameSession?: (id: string, title: string) => void;
  className?: string;
}

export const ChatLayout: React.FC<ChatLayoutProps> = ({
  children,
  sessionTitle,
  folderPath,
  selectedAgent,
  contextPaths,
  isOrchestrateMode,
  sessions = [],
  currentSessionId,
  isSessionsLoading = false,
  onSend,
  onSelectAgent,
  onToggleOrchestrate,
  onFolderClick,
  onNewSession,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
  className = ''
}) => {
  const activeSession = sessions.find((s) => s.id === currentSessionId);
  const displayTitle = sessionTitle ?? activeSession?.title ?? 'MindFlow';

  return (
    <div className={`flex h-screen w-full overflow-hidden bg-[#0a0a0a] ${className}`}>
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        isLoading={isSessionsLoading}
        onNewSession={onNewSession}
        onSelectSession={onSelectSession}
        onDeleteSession={onDeleteSession}
        onRenameSession={onRenameSession}
      />
      
      <main className="flex-1 flex flex-col relative min-w-0">
        {/* Top Bar */}
        <header className="h-16 border-b border-[#2a2a2a] flex items-center justify-between px-6 bg-[#0a0a0a]/95 backdrop-blur-md z-10 sticky top-0">
          <h2 className="text-sm font-semibold text-white tracking-tight">{displayTitle}</h2>
          <div className="flex items-center gap-3">
            <button className="p-2 rounded-lg text-[#b0b0b0] hover:text-white hover:bg-[#2a2a2a] transition-colors">
              <ShareNetwork size={20} />
            </button>
            <button className="p-2 rounded-lg text-[#b0b0b0] hover:text-white hover:bg-[#2a2a2a] transition-colors">
              <Gear size={20} />
            </button>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 pb-48 relative">
          <div className="max-w-4xl mx-auto">
            {children}
          </div>
        </div>

        {/* Input Bar */}
        <div className="absolute bottom-0 left-0 right-0 p-4 pt-12 bg-gradient-to-t from-[#0a0a0a] via-[#0a0a0a] to-transparent z-20">
          <div className="max-w-4xl mx-auto">
            <InputBar
              folderPath={folderPath}
              selectedAgent={selectedAgent}
              contextPaths={contextPaths}
              isOrchestrateMode={isOrchestrateMode}
              onSend={onSend}
              onSelectAgent={onSelectAgent}
              onToggleOrchestrate={onToggleOrchestrate}
              onFolderClick={onFolderClick}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default ChatLayout;
