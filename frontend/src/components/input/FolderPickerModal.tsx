import React, { useState, useEffect, useCallback } from 'react';
import {
  Folder,
  FolderOpen,
  CaretLeft,
  X,
  Check,
  GitBranch,
  ArrowClockwise,
  House,
  MagnifyingGlass,
} from '@phosphor-icons/react';

interface FolderEntry {
  name: string;
  path: string;
  is_dir: boolean;
  is_git_repo: boolean;
}

interface BrowseResponse {
  current_path: string;
  parent_path: string | null;
  entries: FolderEntry[];
}

interface FolderPickerModalProps {
  isOpen: boolean;
  currentPath?: string;
  onSelect: (path: string) => void;
  onClose: () => void;
}

export const FolderPickerModal: React.FC<FolderPickerModalProps> = ({
  isOpen,
  currentPath,
  onSelect,
  onClose,
}) => {
  const [browseData, setBrowseData] = useState<BrowseResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<string>(currentPath || '');
  const [inputPath, setInputPath] = useState<string>(currentPath || '');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const fetchDirectory = useCallback(async (path: string) => {
    setIsLoading(true);
    setError(null);
    setSearchQuery('');
    try {
      const encoded = encodeURIComponent(path);
      const res = await fetch(`/api/v1/filesystem/browse?path=${encoded}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const data: BrowseResponse = await res.json();
      setBrowseData(data);
      setSelectedPath(data.current_path);
      setInputPath(data.current_path);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to browse directory');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load initial directory when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchDirectory(currentPath || '~');
    }
  }, [isOpen, currentPath, fetchDirectory]);

  const handleNavigate = (path: string) => {
    fetchDirectory(path);
  };

  const handleGoHome = () => {
    fetchDirectory('~');
  };

  const handleGoUp = () => {
    if (browseData?.parent_path) {
      fetchDirectory(browseData.parent_path);
    }
  };

  const handleInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputPath.trim()) {
      setSelectedPath(inputPath.trim());
      fetchDirectory(inputPath.trim());
    }
  };

  const handleUseInputAsSelection = () => {
    if (inputPath.trim()) {
      setSelectedPath(inputPath.trim());
    }
  };

  const filteredEntries = browseData?.entries.filter(entry =>
    entry.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    entry.path.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const handleConfirm = () => {
    if (selectedPath) {
      onSelect(selectedPath);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-xl bg-[#1a1a1a] border border-[#2a2a2a] rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a2a]">
          <div className="flex items-center gap-2">
            <FolderOpen className="text-[#0D6E6E]" size={18} weight="fill" />
            <span className="text-[13px] font-semibold text-white">Select Working Directory</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[#2a2a2a] text-[#707070] hover:text-white transition-colors"
          >
            <X size={16} weight="bold" />
          </button>
        </div>

        {/* Path input bar */}
        <form onSubmit={handleInputSubmit} className="px-4 py-2 border-b border-[#2a2a2a] flex items-center gap-2">
          <button
            type="button"
            onClick={handleGoHome}
            className="p-1.5 rounded hover:bg-[#2a2a2a] text-[#707070] hover:text-white transition-colors flex-shrink-0"
            title="Home directory"
          >
            <House size={15} weight="fill" />
          </button>
          <button
            type="button"
            onClick={handleGoUp}
            disabled={!browseData?.parent_path}
            className="p-1.5 rounded hover:bg-[#2a2a2a] text-[#707070] hover:text-white transition-colors flex-shrink-0 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Go up"
          >
            <CaretLeft size={15} weight="bold" />
          </button>
          <input
            type="text"
            value={inputPath}
            onChange={(e) => setInputPath(e.target.value)}
            className="flex-1 bg-[#0a0a0a] border border-[#3a3a3a] rounded px-3 py-1.5 text-[12px] font-mono text-white outline-none focus:border-[#0D6E6E]/50 transition-colors"
            placeholder="/path/to/directory"
            spellCheck={false}
          />
          <button
            type="button"
            onClick={handleUseInputAsSelection}
            disabled={!inputPath.trim()}
            className="p-1.5 rounded hover:bg-[#0D6E6E]/20 text-[#707070] hover:text-[#0D6E6E] transition-colors flex-shrink-0 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Use this path as selection"
          >
            <Check size={15} weight="bold" />
          </button>
          <button
            type="submit"
            className="p-1.5 rounded hover:bg-[#2a2a2a] text-[#707070] hover:text-white transition-colors flex-shrink-0"
            title="Navigate to path"
          >
            <ArrowClockwise size={15} weight="bold" />
          </button>
        </form>

        {/* Search bar */}
        <div className="px-4 py-2 border-b border-[#2a2a2a] flex items-center gap-2">
          <MagnifyingGlass className="text-[#707070]" size={14} weight="bold" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 bg-transparent border-none px-0 py-1 text-[12px] text-white outline-none placeholder-[#505050]"
            placeholder="Search folders in current directory..."
            spellCheck={false}
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="p-1 rounded hover:bg-[#2a2a2a] text-[#707070] hover:text-white transition-colors"
            >
              <X size={12} weight="bold" />
            </button>
          )}
        </div>

        {/* Directory listing */}
        <div className="flex-1 overflow-y-auto min-h-0" style={{ maxHeight: '340px' }}>
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-[#0D6E6E] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-[#0D6E6E] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-[#0D6E6E] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}

          {error && !isLoading && (
            <div className="px-4 py-3">
              <p className="text-[12px] text-red-400">{error}</p>
            </div>
          )}

          {!isLoading && !error && browseData && (
            <>
              {filteredEntries.length === 0 && (
                <div className="flex items-center justify-center py-12">
                  <p className="text-[12px] text-[#505050]">
                    {searchQuery ? 'No matching folders found' : 'No subdirectories found'}
                  </p>
                </div>
              )}

              {filteredEntries.map((entry) => (
                <button
                  key={entry.path}
                  onClick={() => handleNavigate(entry.path)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-[#2a2a2a] transition-colors group ${
                    selectedPath === entry.path ? 'bg-[#2a2a2a]' : ''
                  }`}
                >
                  <div className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: entry.is_git_repo ? '#0D6E6E20' : '#2a2a2a' }}
                  >
                    {entry.is_git_repo ? (
                      <GitBranch className="text-[#0D6E6E]" size={14} weight="fill" />
                    ) : (
                      <Folder className="text-[#707070] group-hover:text-[#b0b0b0]" size={14} weight="fill" />
                    )}
                  </div>
                  <span className={`text-[13px] flex-1 truncate ${
                    entry.is_git_repo ? 'text-[#e0e0e0]' : 'text-[#b0b0b0] group-hover:text-white'
                  }`}>
                    {entry.name}
                  </span>
                  {entry.is_git_repo && (
                    <span className="text-[10px] text-[#0D6E6E] bg-[#0D6E6E]/10 px-1.5 py-0.5 rounded border border-[#0D6E6E]/20 flex-shrink-0">
                      git
                    </span>
                  )}
                </button>
              ))}
            </>
          )}
        </div>

        {/* Selected path + confirm */}
        <div className="px-4 py-3 border-t border-[#2a2a2a] flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-[10px] text-[#505050] uppercase tracking-wider mb-0.5">Selected</p>
            <p className="text-[12px] font-mono text-[#b0b0b0] truncate">
              {selectedPath || 'No directory selected'}
            </p>
          </div>
          <button
            onClick={handleConfirm}
            disabled={!selectedPath}
            className="flex items-center gap-2 px-4 py-2 bg-[#0D6E6E] hover:bg-[#0D6E6E]/80 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-[12px] font-semibold text-white transition-colors flex-shrink-0"
          >
            <Check size={14} weight="bold" />
            Select Folder
          </button>
        </div>
      </div>
    </div>
  );
};

export default FolderPickerModal;
