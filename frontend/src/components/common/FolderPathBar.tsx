import React, { useRef } from 'react';
import { Folder, FolderOpen, X } from 'lucide-react';

interface FolderPathBarProps {
  value: string;
  onChange: (path: string) => void;
}

export const FolderPathBar: React.FC<FolderPathBarProps> = ({ value, onChange }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleBrowse = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const firstFile = files[0];
    const relativePath = (firstFile as File & { webkitRelativePath?: string }).webkitRelativePath;

    if (relativePath) {
      const [root] = relativePath.split('/');
      onChange(root);
    }

    event.target.value = '';
  };

  return (
    <div className="composer-path flex items-center gap-3 px-4 py-3">
      <span className={value ? 'signal-dot' : 'signal-dot idle'} />

      <div className="hidden md:flex items-center" style={{ color: value ? 'var(--text-primary)' : 'var(--text-meta)' }}>
        {value ? <FolderOpen size={14} /> : <Folder size={14} />}
      </div>

      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="/caminho/do/projeto"
        className="min-w-0 flex-1 bg-transparent outline-none"
        style={{
          color: value ? 'var(--text-primary)' : 'var(--text-meta)',
          fontFamily: 'var(--font-mono)',
          fontSize: 12,
        }}
      />

      <button
        type="button"
        className="subtle-button"
        onClick={handleBrowse}
        style={{ minHeight: 30, paddingInline: 12 }}
      >
        <span className="mono-label" style={{ letterSpacing: '0.08em' }}>
          abrir
        </span>
      </button>

      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          className="subtle-button"
          style={{ minHeight: 30, paddingInline: 10 }}
        >
          <X size={14} />
        </button>
      )}

      <input
        ref={fileInputRef}
        type="file"
        // @ts-expect-error webkitdirectory is supported by browsers but absent in React typing
        webkitdirectory=""
        multiple
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />
    </div>
  );
};
