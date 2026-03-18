import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, Dot, MoonStar, SunMedium } from 'lucide-react';
import { useThemeController } from '../theme/useThemeController';

interface TopBarProps {
  title: string;
  agentCount?: number;
  workflowType?: 'parallel' | 'sequential' | 'orchestrator' | 'chain';
  selectedModel: string;
  availableModels: string[];
  onModelChange: (model: string) => void;
  className?: string;
}

const WORKFLOW_LABELS: Record<string, string> = {
  parallel: 'parallel',
  sequential: 'sequential',
  orchestrator: 'orchestrator',
  chain: 'chain',
};

export const TopBar: React.FC<TopBarProps> = ({
  title,
  agentCount = 0,
  workflowType,
  selectedModel,
  availableModels,
  onModelChange,
}) => {
  const [modelOpen, setModelOpen] = useState(false);
  const modelMenuRef = useRef<HTMLDivElement>(null);
  const themeButtonRef = useRef<HTMLButtonElement>(null);
  const { theme, isTransitioning, toggleThemeFromElement } = useThemeController();
  const hasActiveAgents = agentCount > 0;

  const activeLabel = useMemo(() => {
    return `${agentCount} ativo${agentCount > 1 ? 's' : ''}`;
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
      className="topbar-shell flex flex-wrap items-center gap-3 border-b px-4 py-4 md:px-6"
      style={{
        borderColor: 'var(--line-primary)',
      }}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-3">
          <h1
            className="truncate"
            style={{
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-brand)',
              fontSize: 32,
              fontWeight: 600,
              letterSpacing: '-0.03em',
            }}
          >
            {title}
          </h1>

          {hasActiveAgents && (
            <span className="event-badge">
              <span className="signal-dot" />
              {activeLabel}
            </span>
          )}

          {workflowType && workflowType !== 'orchestrator' && (
            <span className="event-badge">
              {WORKFLOW_LABELS[workflowType] ?? workflowType}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2" ref={modelMenuRef}>
        <button
          ref={themeButtonRef}
          type="button"
          className="theme-toggle-button"
          onClick={() => toggleThemeFromElement(themeButtonRef.current)}
          disabled={isTransitioning}
        >
          <span className="theme-toggle-core">
            {theme === 'dark' ? <MoonStar size={14} /> : <SunMedium size={14} />}
          </span>
          <span className="mono-label" style={{ letterSpacing: '0.08em' }}>
            {theme}
          </span>
        </button>

        <div className="relative">
          <button
            type="button"
            className="subtle-button"
            onClick={() => setModelOpen((value) => !value)}
          >
            <span className="mono-label" style={{ letterSpacing: '0.08em' }}>
              model
            </span>
            <span
              className="truncate"
              style={{
                maxWidth: 180,
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: 'calc(13px * var(--font-scale, 1))',
              }}
            >
              {selectedModel}
            </span>
            <ChevronDown size={14} />
          </button>

          {modelOpen && (
            <div
              className="lab-dropdown absolute right-0 top-[calc(100%+10px)] z-50 min-w-[240px] overflow-hidden p-2"
            >
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
                    className="lab-dropdown-option flex w-full items-center gap-3 rounded-[14px] border px-3 py-3 text-left"
                    style={{
                      marginBottom: 6,
                      borderColor: selected ? 'var(--line-strong)' : 'transparent',
                      background: selected ? 'var(--surface-glass)' : 'transparent',
                    }}
                  >
                    <Dot
                      size={18}
                      style={{ color: selected ? 'var(--text-primary)' : 'var(--text-ghost)' }}
                    />
                    <span
                      style={{
                        color: selected ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 'calc(13px * var(--font-scale, 1))',
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
      </div>
    </div>
  );
};

export default TopBar;
