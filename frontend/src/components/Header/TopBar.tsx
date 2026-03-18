import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, MoonStar, Settings, SunMedium } from 'lucide-react';
import { useThemeController } from '../theme/useThemeController';

interface TopBarProps {
  title: string;
  agentCount?: number;
  workflowType?: 'parallel' | 'sequential' | 'orchestrator' | 'chain';
  selectedModel: string;
  availableModels: string[];
  onModelChange: (model: string) => void;
  className?: string;
  folderPath?: string;
}

export const TopBar: React.FC<TopBarProps> = ({
  title,
  agentCount = 0,
  selectedModel,
  availableModels,
  onModelChange,
  folderPath,
}) => {
  const [modelOpen, setModelOpen] = useState(false);
  const modelMenuRef = useRef<HTMLDivElement>(null);
  const themeButtonRef = useRef<HTMLButtonElement>(null);
  const { theme, isTransitioning, toggleThemeFromElement } = useThemeController();

  const activeLabel = useMemo(() => {
    return `${agentCount} active`;
  }, [agentCount]);

  useEffect(() => {
    if (!modelOpen) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (!modelMenuRef.current?.contains(event.target as Node)) {
        setModelOpen(false);
      }
    };

    window.addEventListener('pointerdown', handlePointerDown);
    return () => window.removeEventListener('pointerdown', handlePointerDown);
  }, [modelOpen]);

  return (
    <div
      className="topbar-shell flex items-center gap-3 border-b px-4 py-3 md:px-6"
      style={{ borderColor: 'var(--line-primary)' }}
    >
      {/* Title */}
      <div className="min-w-0 flex-1">
        <h1
          className="truncate"
          style={{
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-brand)',
            fontSize: 20,
            fontWeight: 500,
            letterSpacing: '-0.01em',
          }}
        >
          {title}
        </h1>
        {folderPath && (
          <div
            className="truncate"
            style={{
              color: 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              marginTop: 2,
            }}
          >
            {folderPath}
          </div>
        )}
      </div>

      {/* Right side controls */}
      <div className="flex items-center gap-2" ref={modelMenuRef}>
        {agentCount > 0 && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '3px 10px',
              border: '1px solid rgba(13,110,110,0.2)',
              borderRadius: 20,
              background: 'var(--teal-soft)',
              color: '#0D6E6E',
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              letterSpacing: '0.06em',
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#0D6E6E', flexShrink: 0 }} />
            {activeLabel}
          </span>
        )}

        {/* Theme toggle */}
        <button
          ref={themeButtonRef}
          type="button"
          className="theme-toggle-button"
          onClick={() => toggleThemeFromElement(themeButtonRef.current)}
          disabled={isTransitioning}
        >
          <span className="theme-toggle-core">
            {theme === 'dark' ? <MoonStar size={13} /> : <SunMedium size={13} />}
          </span>
          <span className="mono-label hidden md:inline" style={{ letterSpacing: '0.08em' }}>
            {theme}
          </span>
        </button>

        {/* Model selector */}
        <div className="relative">
          <button
            type="button"
            className="subtle-button"
            onClick={() => setModelOpen((v) => !v)}
          >
            <span className="mono-label hidden md:inline" style={{ letterSpacing: '0.08em' }}>
              model
            </span>
            <span
              className="truncate"
              style={{
                maxWidth: 160,
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
              }}
            >
              {selectedModel}
            </span>
            <ChevronDown size={13} />
          </button>

          {modelOpen && (
            <div className="lab-dropdown absolute right-0 top-[calc(100%+8px)] z-50 min-w-[220px] overflow-hidden p-2">
              {availableModels.map((model) => {
                const selected = model === selectedModel;
                return (
                  <button
                    key={model}
                    type="button"
                    onClick={() => {
                      onModelChange(model);
                      setModelOpen(false);
                    }}
                    className="lab-dropdown-option flex w-full items-center gap-2 rounded-[10px] border px-3 py-2 text-left"
                    style={{
                      marginBottom: 4,
                      borderColor: selected ? 'var(--line-strong)' : 'transparent',
                      background: selected ? 'var(--surface-glass)' : 'transparent',
                    }}
                  >
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: selected ? '#0D6E6E' : 'var(--line-primary)',
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        color: selected ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 12,
                        lineHeight: 1.5,
                      }}
                    >
                      {model}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Settings shortcut (visible on small screens) */}
        <button
          type="button"
          className="subtle-button md:hidden"
          style={{ padding: '0 8px', minWidth: 36 }}
        >
          <Settings size={14} />
        </button>
      </div>
    </div>
  );
};

export default TopBar;
