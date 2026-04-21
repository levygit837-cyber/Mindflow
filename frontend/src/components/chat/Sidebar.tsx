import React, { useRef, useState } from 'react';
import { Plus, Chat, DotsThree, User, Trash, PencilSimple, X, Check } from '@phosphor-icons/react';
import { ChatSession } from '../../types/backend';

interface SidebarProps {
  sessions?: ChatSession[];
  currentSessionId?: string | null;
  isLoading?: boolean;
  onNewSession?: () => void;
  onSelectSession?: (id: string) => void;
  onDeleteSession?: (id: string) => void;
  onRenameSession?: (id: string, title: string) => void;
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions = [],
  currentSessionId,
  isLoading = false,
  onNewSession,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
  className = '',
}) => {
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const menuRef = useRef<HTMLDivElement | null>(null);
  const editInputRef = useRef<HTMLInputElement | null>(null);

  const handleMenuToggle = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setMenuOpenId((prev) => (prev === id ? null : id));
  };

  const handleRenameStart = (e: React.MouseEvent, session: ChatSession) => {
    e.stopPropagation();
    setMenuOpenId(null);
    setEditingId(session.id);
    setEditValue(session.title || '');
    setTimeout(() => editInputRef.current?.select(), 0);
  };

  const handleRenameSubmit = (id: string) => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== sessions.find((s) => s.id === id)?.title) {
      onRenameSession?.(id, trimmed);
    }
    setEditingId(null);
  };

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setMenuOpenId(null);
    onDeleteSession?.(id);
  };

  return (
    <aside
      className={`w-[260px] bg-[#1a1a1a] border-r border-[#2a2a2a] flex flex-col shrink-0 h-full z-20 shadow-xl shadow-black/50 ${className}`}
      onClick={() => setMenuOpenId(null)}
    >
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
          <span className="text-[#707070] text-[11px] uppercase font-semibold tracking-[0.05em]">
            Recent Sessions
          </span>
        </div>

        {isLoading && sessions.length === 0 && (
          <div className="flex flex-col gap-1.5 px-2 mt-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 rounded-md bg-[#2a2a2a] animate-pulse" />
            ))}
          </div>
        )}

        <ul className="space-y-0.5">
          {sessions.map((session) => {
            const isActive = session.id === currentSessionId;
            const isEditing = editingId === session.id;
            const isMenuOpen = menuOpenId === session.id;

            return (
              <li
                key={session.id}
                onClick={() => !isEditing && onSelectSession?.(session.id)}
                className={`
                  group relative rounded-md flex items-center px-2 py-2 cursor-pointer
                  hover:bg-[#2d2d2d] transition-colors duration-150
                  ${isActive ? 'bg-[#2d2d2d]' : ''}
                `}
              >
                <Chat
                  className={isActive ? 'text-[#0D6E6E] shrink-0' : 'text-[#606060] shrink-0'}
                  size={16}
                  weight={isActive ? 'bold' : 'regular'}
                  style={{ marginRight: '10px' }}
                />

                {isEditing ? (
                  <div className="flex items-center gap-1 flex-1 min-w-0">
                    <input
                      ref={editInputRef}
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRenameSubmit(session.id);
                        if (e.key === 'Escape') setEditingId(null);
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="flex-1 min-w-0 bg-[#3a3a3a] border border-[#0D6E6E]/50 rounded px-1.5 py-0.5 text-[12px] text-white outline-none"
                      autoFocus
                    />
                    <button
                      onClick={(e) => { e.stopPropagation(); handleRenameSubmit(session.id); }}
                      className="p-0.5 text-[#0D6E6E] hover:text-white"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setEditingId(null); }}
                      className="p-0.5 text-[#707070] hover:text-white"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <>
                    <span
                      className={`text-[13px] truncate flex-1 ${
                        isActive ? 'text-white font-medium' : 'text-[#a0a0a0]'
                      }`}
                    >
                      {session.title || 'Untitled Chat'}
                    </span>

                    {/* Context menu trigger */}
                    <button
                      onClick={(e) => handleMenuToggle(e, session.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-[#707070] hover:text-white transition-opacity rounded shrink-0"
                    >
                      <DotsThree size={18} />
                    </button>

                    {/* Dropdown menu */}
                    {isMenuOpen && (
                      <div
                        ref={menuRef}
                        className="absolute right-2 top-8 z-50 bg-[#252525] border border-[#3a3a3a] rounded-lg shadow-xl py-1 w-36"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={(e) => handleRenameStart(e, session)}
                          className="w-full flex items-center gap-2 px-3 py-2 text-[12px] text-[#c0c0c0] hover:text-white hover:bg-[#3a3a3a] transition-colors"
                        >
                          <PencilSimple size={14} />
                          Rename
                        </button>
                        <button
                          onClick={(e) => handleDelete(e, session.id)}
                          className="w-full flex items-center gap-2 px-3 py-2 text-[12px] text-red-400 hover:text-red-300 hover:bg-[#3a3a3a] transition-colors"
                        >
                          <Trash size={14} />
                          Delete
                        </button>
                      </div>
                    )}
                  </>
                )}
              </li>
            );
          })}
        </ul>

        {!isLoading && sessions.length === 0 && (
          <p className="text-[#505050] text-[12px] text-center mt-8 px-4">
            No sessions yet. Start a new chat!
          </p>
        )}
      </div>

      {/* User Footer */}
      <div className="p-4 border-t border-[#2a2a2a] bg-[#1a1a1a]/80 backdrop-blur-sm">
        <button className="w-full flex items-center gap-3 hover:bg-[#2a2a2a] p-2 -m-2 rounded-lg transition-colors text-left cursor-pointer">
          <div className="w-8 h-8 rounded-full bg-[#3a3a3a] border border-[#3a3a3a] flex items-center justify-center">
            <User className="text-[#b0b0b0]" size={16} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">Local</p>
            <p className="text-[11px] text-[#707070] truncate">MindFlow Dev</p>
          </div>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
