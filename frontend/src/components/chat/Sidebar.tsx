import React from 'react';
import { Plus, Chat, Code, ChartLineUp, DotsThree, User } from '@phosphor-icons/react';

interface Session {
  id: string;
  title: string;
  icon?: 'chat' | 'code' | 'analysis';
  isActive?: boolean;
}

interface SidebarProps {
  sessions?: Session[];
  currentSessionId?: string;
  onNewSession?: () => void;
  onSelectSession?: (id: string) => void;
  className?: string;
}

const iconMap = {
  chat: Chat,
  code: Code,
  analysis: ChartLineUp,
};

export const Sidebar: React.FC<SidebarProps> = ({
  sessions = [],
  currentSessionId,
  onNewSession,
  onSelectSession,
  className = ''
}) => {
  const defaultSessions: Session[] = [
    { id: '1', title: 'Research Project Alpha', icon: 'chat', isActive: true },
    { id: '2', title: 'Database Sharding Script', icon: 'code' },
    { id: '3', title: 'Q3 Financial Analysis', icon: 'analysis' },
  ];

  const displaySessions = sessions.length > 0 ? sessions : defaultSessions;

  return (
    <aside className={`w-[260px] bg-[#1a1a1a] border-r border-[#2a2a2a] flex flex-col shrink-0 h-full z-20 shadow-xl shadow-black/50 ${className}`}>
      {/* Header / Logo */}
      <div className="h-16 flex items-center px-4 border-b border-[#2a2a2a]">
        <div className="w-8 h-8 rounded bg-[#2a2a2a] border border-[#3a3a3a] justify-center items-center flex mr-3">
          <span className="text-[#0D6E6E] text-xl font-bold leading-none mt-[-2px]">M</span>
        </div>
        <span className="font-semibold text-[15px] tracking-wide">MindFlow</span>
      </div>

      <div className="p-4">
        <button 
          onClick={onNewSession}
          className="w-full bg-[#2a2a2a] hover:bg-[#3a3a3a] text-white rounded-lg py-2.5 px-3 flex items-center justify-between transition-colors duration-150"
        >
          <span className="text-[13px] font-medium">New Session</span>
          <Plus className="text-[#b0b0b0]" size={18} />
        </button>
      </div>

      {/* Recent Sessions */}
      <div className="flex-1 overflow-y-auto px-2">
        <div className="px-2 mb-2 mt-2">
          <span className="text-[#707070] text-[11px] uppercase font-semibold tracking-[0.05em]">Recent Sessions</span>
        </div>
        
        <ul className="space-y-0.5">
          {displaySessions.map((session) => {
            const Icon = session.icon ? iconMap[session.icon] : Chat;
            const isActive = session.id === currentSessionId || session.isActive;
            
            return (
              <li 
                key={session.id}
                onClick={() => onSelectSession?.(session.id)}
                className={`
                  group relative rounded-md flex items-center px-2 py-2 cursor-pointer 
                  hover:bg-[#3a3a3a] transition-colors duration-150
                  ${isActive ? 'bg-[#3a3a3a]/30' : ''}
                `}
              >
                <Icon 
                  className={isActive ? 'text-[#0D6E6E]' : 'text-[#b0b0b0]'} 
                  size={20} 
                  weight={isActive ? 'bold' : 'regular'}
                  style={{ marginRight: '12px' }}
                />
                <span className={`text-[13px] truncate flex-1 ${isActive ? 'text-white font-medium' : 'text-[#b0b0b0]'}`}>
                  {session.title}
                </span>
                <button className="opacity-0 group-hover:opacity-100 p-1 text-[#b0b0b0] hover:text-white transition-opacity rounded">
                  <DotsThree size={20} />
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* User Footer */}
      <div className="p-4 border-t border-[#2a2a2a] bg-[#1a1a1a]/80 backdrop-blur-sm">
        <button className="w-full flex items-center gap-3 hover:bg-[#2a2a2a] p-2 -m-2 rounded-lg transition-colors text-left cursor-pointer">
          <div className="w-8 h-8 rounded-full bg-[#3a3a3a] border border-[#3a3a3a] flex items-center justify-center">
            <User className="text-[#b0b0b0]" size={16} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">Alex Vance</p>
            <p className="text-[11px] text-[#707070] truncate">Enterprise Plan</p>
          </div>
          <div className="bg-[#0D6E6E]/10 border border-[#0D6E6E]/30 px-1.5 py-0.5 rounded text-[10px] font-bold text-[#0D6E6E] uppercase tracking-wider">
            Pro
          </div>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
