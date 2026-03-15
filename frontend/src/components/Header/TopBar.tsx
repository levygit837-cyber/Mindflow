import React, { useMemo, useState } from 'react';
import { ChevronDown, Dot } from 'lucide-react';

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

  const activeLabel = useMemo(() => {
    if (agentCount <= 0) return 'idle';
    return `${agentCount} ativo${agentCount > 1 ? 's' : ''}`;
  }, [agentCount]);

  return (
    <div
      className="topbar-shell flex flex-wrap items-center gap-3 border-b px-4 py-4 md:px-6"
      style={{
        borderColor: 'var(--line-primary)',
      }}
    >
      <div className="min-w-0 flex-1">
        <div className="mono-label mb-2">chat / live trace</div>
        <div className="flex flex-wrap items-center gap-3">
          <h1
            className="truncate"
            style={{
              color: 'var(--text-primary)',
              fontSize: 18,
              fontWeight: 600,
              letterSpacing: '-0.03em',
            }}
          >
            {title}
          </h1>

          <span className="event-badge">
            <span className={`signal-dot ${agentCount > 0 ? '' : 'idle'}`} />
            {activeLabel}
          </span>

          {workflowType && (
            <span className="event-badge">
              <span style={{ color: 'var(--text-meta)' }}>---</span>
              {WORKFLOW_LABELS[workflowType] ?? workflowType}
            </span>
          )}
        </div>
      </div>

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
              fontSize: 12,
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
                    background: selected ? 'rgba(255, 255, 255, 0.04)' : 'transparent',
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
    </div>
  );
};

export default TopBar;
