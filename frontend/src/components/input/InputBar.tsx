import React, { useState, useRef, useEffect } from 'react';
import { Folder, CaretUp, MagicWand, PaperPlaneRight } from '@phosphor-icons/react';
import { AgentType } from '../../lib/constants';
import { AgentPill } from './AgentPill';
import { ContextPill } from './ContextPill';

interface InputBarProps {
  folderPath?: string;
  selectedAgent?: AgentType | null;
  contextPaths?: string[];
  isOrchestrateMode?: boolean;
  onSend?: (text: string) => void | Promise<void>;
  onSelectAgent?: (agent: AgentType | null) => void;
  onToggleOrchestrate?: () => void;
  onFolderClick?: () => void;
  className?: string;
}

export const InputBar: React.FC<InputBarProps> = ({
  folderPath = '~',
  selectedAgent = null,
  contextPaths = [],
  isOrchestrateMode = false,
  onSend,
  onSelectAgent,
  onToggleOrchestrate,
  onFolderClick,
  className = ''
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 128)}px`;
    }
  }, [text]);

  const handleSend = async () => {
    if (text.trim()) {
      const messageToSend = text;
      setText('');
      await onSend?.(messageToSend);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const agentTypes: AgentType[] = ['coder', 'analyst', 'researcher'];

  return (
    <div className={`pointer-events-auto ${className}`}>
      {/* Context Pills */}
      {contextPaths.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2 px-1">
          {contextPaths.map((path, index) => (
            <ContextPill key={index} path={path} />
          ))}
        </div>
      )}

      <div className="
        bg-[#2a2a2a] 
        border border-[#3a3a3a] 
        rounded-[12px] 
        p-3 pt-4 
        flex flex-col gap-3 
        shadow-[0_8px_30px_rgba(0,0,0,0.5)]
        focus-within:ring-1 
        focus-within:ring-[#0D6E6E]/50 
        transition-all
      ">
        {/* Text Input Area */}
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          className="
            w-full 
            bg-transparent 
            text-white 
            placeholder-[#505050] 
            text-[15px] 
            resize-none 
            outline-none 
            max-h-32 
            px-1
          "
          placeholder="Ask MindFlow anything... (e.g. 'Research X and let Analyst compare with Y')"
        />

        <div className="flex items-center justify-between mt-2 flex-wrap gap-2">
          {/* Utility Left side */}
          <div className="flex items-center gap-3">
            {/* Context / Folder Path Selector */}
            <button
              onClick={onFolderClick}
              className="
              flex items-center gap-1.5 
              px-2 py-1.5 
              hover:bg-[#3a3a3a] 
              rounded 
              border border-transparent 
              hover:border-[#3a3a3a] 
              transition-colors 
              group
            ">
              <Folder className="text-[#0D6E6E]" weight="fill" size={16} />
              <span className="text-[#b0b0b0] font-mono text-[11px] mt-0.5 group-hover:text-white transition-colors truncate max-w-[150px] sm:max-w-xs">
                {folderPath}
              </span>
              <CaretUp className="text-[#707070] ml-1" weight="bold" size={10} />
            </button>

            {/* Separator */}
            <div className="w-px h-4 bg-[#3a3a3a] hidden sm:block" />

            {/* Agent Selector Pills */}
            <div className="hidden sm:flex items-center gap-1.5">
              <span className="text-[10px] text-[#707070] uppercase font-semibold mr-1">Direct:</span>
              
              {agentTypes.map((agentType) => (
                <AgentPill
                  key={agentType}
                  type={agentType}
                  isSelected={selectedAgent === agentType}
                  onClick={() => onSelectAgent?.(selectedAgent === agentType ? null : agentType)}
                />
              ))}
            </div>
          </div>

          {/* Utility Right side */}
          <div className="flex items-center gap-2">
            {/* Orchestrate Toggle */}
            <button
              onClick={onToggleOrchestrate}
              className={`
                px-3 py-1.5 
                rounded 
                text-[12px] 
                font-medium 
                border 
                transition-colors 
                flex items-center gap-1.5
                ${isOrchestrateMode 
                  ? 'bg-[#0D6E6E]/10 border-[#0D6E6E]/30 text-[#0D6E6E] hover:bg-[#0D6E6E]/20' 
                  : 'bg-[#1a1a1a] border-[#3a3a3a] text-[#b0b0b0] hover:text-white'
                }
              `}
            >
              <MagicWand weight="fill" size={14} />
              Orchestrate Mode
            </button>

            {/* Send Button */}
            <button
              onClick={handleSend}
              className="
                w-8 h-8 
                rounded-lg 
                bg-[#0a0a0a] 
                border border-[#3a3a3a] 
                hover:border-[#0D6E6E] 
                hover:bg-[#0D6E6E]/10 
                flex items-center justify-center 
                text-[#0D6E6E] 
                transition-all 
                shadow-sm
              ">
              <PaperPlaneRight weight="bold" size={16} />
            </button>
          </div>
        </div>
      </div>

      <div className="mt-2 text-center">
        <p className="text-[10px] text-[#707070] font-medium">MindFlow AI Workspace. Data is transmitted securely.</p>
      </div>
    </div>
  );
};

export default InputBar;
