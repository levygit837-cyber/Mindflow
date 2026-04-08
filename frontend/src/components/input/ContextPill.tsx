import React from 'react';
import { FileText, FileCode, Folder, Link } from '@phosphor-icons/react';

interface ContextPillProps {
  path: string;
  type?: 'file' | 'folder' | 'link';
  onRemove?: () => void;
  className?: string;
}

const iconMap = {
  file: FileText,
  folder: Folder,
  link: Link,
};

const getFileIcon = (path: string) => {
  if (path.endsWith('.ts') || path.endsWith('.tsx') || path.endsWith('.js') || path.endsWith('.jsx')) {
    return FileCode;
  }
  return FileText;
};

export const ContextPill: React.FC<ContextPillProps> = ({ 
  path, 
  type = 'file',
  onRemove,
  className = ''
}) => {
  const Icon = type === 'file' ? getFileIcon(path) : iconMap[type];
  const displayName = path.split('/').pop() || path;
  
  return (
    <span 
      className={`
        inline-flex items-center gap-1.5 
        px-2.5 py-1 
        bg-[#3a3a3a] 
        border border-[#2a2a2a] 
        rounded-full 
        text-[12px] 
        text-[#b0b0b0]
        ${className}
      `}
    >
      <Icon size={14} />
      <span className="truncate max-w-[150px]">{displayName}</span>
      {onRemove && (
        <button 
          onClick={onRemove}
          className="ml-1 text-[#707070] hover:text-white transition-colors"
        >
          ×
        </button>
      )}
    </span>
  );
};

export default ContextPill;
