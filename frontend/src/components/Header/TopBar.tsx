import React, { useState } from 'react';
import { GitBranch, Cpu, ChevronDown } from 'lucide-react';

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
  parallel: 'Parallel',
  sequential: 'Sequential',
  orchestrator: 'Orchestrator',
  chain: 'Chain',
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

  return (
    <div
      className="flex items-center flex-shrink-0"
      style={{
        padding: '14px 24px',
        borderBottom: '1px solid #1A1545',
        gap: 12,
        backgroundColor: '#080614',
      }}
    >
      {/* ── Left: Title + agents badge ────────────────── */}
      <div className="flex items-center flex-1 min-w-0" style={{ gap: 10 }}>
        <h1
          style={{
            color: '#EDE9FF',
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: 16,
            fontWeight: 600,
            margin: 0,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {title}
        </h1>

        {agentCount > 0 && (
          <div
            className="flex items-center flex-shrink-0"
            style={{
              backgroundColor: '#0A1520',
              borderRadius: 20,
              padding: '4px 10px',
              gap: 6,
            }}
          >
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                backgroundColor: '#22D3EE',
              }}
            />
            <span
              style={{
                color: '#22D3EE',
                fontFamily: 'Space Grotesk, sans-serif',
                fontSize: 11,
                fontWeight: 500,
              }}
            >
              {agentCount} {agentCount === 1 ? 'agent' : 'agents'} active
            </span>
          </div>
        )}
      </div>

      {/* ── Right: Workflow badge + Model selector ──── */}
      <div className="flex items-center flex-shrink-0" style={{ gap: 8 }}>
        {workflowType && (
          <div
            className="flex items-center"
            style={{
              backgroundColor: '#0F1B2D',
              border: '1px solid #1A3A5C',
              borderRadius: 6,
              padding: '6px 10px',
              gap: 6,
            }}
          >
            <GitBranch size={12} color="#22D3EE" />
            <span
              style={{
                color: '#22D3EE',
                fontFamily: 'Space Grotesk, sans-serif',
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {WORKFLOW_LABELS[workflowType] ?? workflowType}
            </span>
          </div>
        )}

        {/* Model selector */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setModelOpen((o) => !o)}
            className="flex items-center"
            style={{
              backgroundColor: '#130F28',
              border: '1px solid #2A1F50',
              borderRadius: 8,
              padding: '7px 12px',
              gap: 6,
              cursor: 'pointer',
            }}
          >
            <Cpu size={13} color="#A78BFA" />
            <span
              style={{
                color: '#A78BFA',
                fontFamily: 'Space Grotesk, sans-serif',
                fontSize: 12,
                fontWeight: 500,
                maxWidth: 160,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {selectedModel}
            </span>
            <ChevronDown size={12} color="#4D4575" />
          </button>

          {modelOpen && (
            <div
              style={{
                position: 'absolute',
                right: 0,
                top: 'calc(100% + 6px)',
                backgroundColor: '#130F28',
                border: '1px solid #2A1F50',
                borderRadius: 8,
                overflow: 'hidden',
                zIndex: 50,
                minWidth: 200,
              }}
            >
              {availableModels.map((m) => (
                <button
                  key={m}
                  onClick={() => { onModelChange(m); setModelOpen(false); }}
                  className="w-full text-left"
                  style={{
                    padding: '9px 14px',
                    backgroundColor: m === selectedModel ? '#1D1840' : 'transparent',
                    color: m === selectedModel ? '#A78BFA' : '#8B81C0',
                    fontFamily: 'Space Grotesk, sans-serif',
                    fontSize: 12,
                    fontWeight: 500,
                    border: 'none',
                    cursor: 'pointer',
                    display: 'block',
                    width: '100%',
                  }}
                >
                  {m}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TopBar;
