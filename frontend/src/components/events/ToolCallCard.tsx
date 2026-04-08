import React, { useState } from 'react';
import { AGENTS, AgentType } from '../../lib/constants';
import { CaretDown, CaretUp, Globe, Terminal, CheckCircle } from '@phosphor-icons/react';

interface ToolCallCardProps {
  agentType: AgentType;
  toolName: string;
  status: 'pending' | 'running' | 'success' | 'error';
  input: Record<string, unknown>;
  output?: string;
  error?: string;
  className?: string;
}

const iconMap = {
  web_search: Globe,
  browser_search: Globe,
  execute_code: Terminal,
  shell: Terminal,
  command: Terminal,
  default: Terminal,
};

export const ToolCallCard: React.FC<ToolCallCardProps> = ({
  agentType,
  toolName,
  status,
  input,
  output,
  error,
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const agent = AGENTS[agentType];
  
  const Icon = iconMap[toolName as keyof typeof iconMap] || iconMap.default;
  
  const statusColors = {
    pending: '#707070',
    running: agent.color,
    success: '#2D8F5E',
    error: '#e74c3c',
  };
  
  return (
    <div 
      className={`bg-[#2a2a2a] border border-[#2a2a2a] rounded-r-lg overflow-hidden ${className}`}
      style={{ borderLeftWidth: '3px', borderLeftColor: agent.color }}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-[#3a3a3a] transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon style={{ color: agent.color }} size={20} weight="bold" />
          <span className="text-sm font-medium text-white">{toolName}</span>
          <span 
            className="px-1.5 py-0.5 rounded text-[10px] border"
            style={{ 
              backgroundColor: `${statusColors[status]}15`,
              borderColor: `${statusColors[status]}40`,
              color: statusColors[status]
            }}
          >
            {status}
          </span>
        </div>
        {isExpanded ? (
          <CaretUp className="text-[#707070]" size={16} weight="bold" />
        ) : (
          <CaretDown className="text-[#707070]" size={16} weight="bold" />
        )}
      </button>
      
      {isExpanded && (
        <div className="p-3 border-t border-[#2a2a2a]">
          <div className="space-y-3">
            {/* Input section */}
            {Object.keys(input).length > 0 && (
              <div>
                <span className="text-[10px] text-[#707070] uppercase tracking-wider mb-1 block">Input</span>
                <div className="bg-[#1e1e1e] rounded-lg p-3 font-mono text-[12px] overflow-x-auto">
                  <pre className="text-[#66d9ef] whitespace-pre-wrap">
                    {JSON.stringify(input, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Output section */}
            <div>
              <span className="text-[10px] text-[#707070] uppercase tracking-wider mb-1 block">Output</span>
              <div className="bg-[#1e1e1e] rounded-lg p-3 font-mono text-[12px] overflow-x-auto">
                {status === 'success' && output && (
                  <>
                    <div className="flex items-center gap-2 mb-2 text-[#707070]">
                      <CheckCircle className="text-[#2D8F5E]" size={16} />
                      <span>Execution completed</span>
                    </div>
                    <pre className="text-[#a6e22e] whitespace-pre-wrap">{output}</pre>
                  </>
                )}
                {status === 'error' && error && (
                  <pre className="text-[#e74c3c] whitespace-pre-wrap">{error}</pre>
                )}
                {(status === 'pending' || status === 'running') && (
                  <pre className="text-[#75715e]">// Waiting for execution...</pre>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ToolCallCard;
