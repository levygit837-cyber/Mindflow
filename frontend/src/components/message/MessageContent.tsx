/**
 * MessageContent component - Renders parsed message blocks with dynamic visualizations
 * Supports markdown rendering and syntax highlighting for code blocks
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { parseMessageContent } from '../../lib/messageParser';
import { MessageBlock } from '../../types/messageParser';
import { ThinkingBlock } from '../blocks/ThinkingBlock';
import { ToolCallCard } from '../events/ToolCallCard';
import { DelegationCard } from '../blocks/DelegationCard';
import { AgentType } from '../../types/backend';

interface MessageContentProps {
  content: string;
  agentType?: AgentType;
}

const BlockRenderer: React.FC<{ block: MessageBlock; agentType?: AgentType }> = ({ block, agentType }) => {
  switch (block.type) {
    case 'thinking':
      return (
        <ThinkingBlock
          agentType={agentType || 'orchestrator'}
          reasoning={block.content}
          isExpanded={false}
          onToggle={() => {}}
        />
      );

    case 'tool_call':
      return (
        <ToolCallCard
          agentType={agentType || 'orchestrator'}
          toolName={block.metadata?.title || 'Unknown Tool'}
          status="success"
          input={block.metadata ? { description: block.content } : {}}
          output={block.content}
        />
      );

    case 'delegation':
      return (
        <DelegationCard
          fromAgent={agentType || 'orchestrator'}
          toAgent="coder"
          strategy="single"
          tools={[]}
          context={block.content}
        />
      );

    case 'code':
      return (
        <div className="bg-[#0d1117] border border-[#30363d] rounded-lg my-2 overflow-hidden">
          {block.metadata?.title && (
            <div className="flex items-center gap-2 px-4 py-2 bg-[#161b22] border-b border-[#30363d]">
              <span className="text-[10px] text-[#8b949e] uppercase tracking-wider">Code</span>
              <span className="text-[11px] text-[#c9d1d9]">{block.metadata.title}</span>
            </div>
          )}
          <SyntaxHighlighter
            language={block.metadata?.title || 'text'}
            style={vscDarkPlus}
            customStyle={{
              margin: 0,
              padding: '1rem',
              fontSize: '12px',
              lineHeight: '1.5',
            }}
            showLineNumbers
          >
            {block.content}
          </SyntaxHighlighter>
        </div>
      );

    case 'error':
      return (
        <div className="bg-[#1a1a1a] border border-[#4a2c2c] rounded-lg p-4 my-2">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] text-[#ff6b6b] uppercase tracking-wider">Error</span>
            {block.metadata?.title && (
              <span className="text-[11px] text-[#ff6b6b]">{block.metadata.title}</span>
            )}
          </div>
          <p className="text-[12px] text-[#ff6b6b] whitespace-pre-wrap">{block.content}</p>
        </div>
      );

    case 'warning':
      return (
        <div className="bg-[#1a1a1a] border border-[#4a4c2c] rounded-lg p-4 my-2">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] text-[#ffd93d] uppercase tracking-wider">Warning</span>
            {block.metadata?.title && (
              <span className="text-[11px] text-[#ffd93d]">{block.metadata.title}</span>
            )}
          </div>
          <p className="text-[12px] text-[#ffd93d] whitespace-pre-wrap">{block.content}</p>
        </div>
      );

    case 'info':
      return (
        <div className="bg-[#1a1a1a] border border-[#2c4a4a] rounded-lg p-4 my-2">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] text-[#4dabf7] uppercase tracking-wider">Info</span>
            {block.metadata?.title && (
              <span className="text-[11px] text-[#4dabf7]">{block.metadata.title}</span>
            )}
          </div>
          <p className="text-[12px] text-[#4dabf7] whitespace-pre-wrap">{block.content}</p>
        </div>
      );

    case 'success':
      return (
        <div className="bg-[#1a1a1a] border border-[#2c4a2c] rounded-lg p-4 my-2">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] text-[#51cf66] uppercase tracking-wider">Success</span>
            {block.metadata?.title && (
              <span className="text-[11px] text-[#51cf66]">{block.metadata.title}</span>
            )}
          </div>
          <p className="text-[12px] text-[#51cf66] whitespace-pre-wrap">{block.content}</p>
        </div>
      );

    case 'plain':
    default:
      return (
        <div className="text-[14px] text-[#e0e0e0] leading-relaxed prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Custom styling for markdown elements
              h1: ({ children }) => <h1 className="text-xl font-bold text-white mt-4 mb-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-lg font-bold text-white mt-3 mb-2">{children}</h2>,
              h3: ({ children }) => <h3 className="text-base font-bold text-white mt-2 mb-1">{children}</h3>,
              h4: ({ children }) => <h4 className="text-sm font-bold text-white mt-2 mb-1">{children}</h4>,
              p: ({ children }) => <p className="mb-2">{children}</p>,
              strong: ({ children }) => <strong className="font-bold text-white">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
              code: ({ children }) => (
                <code className="bg-[#0d1117] text-[#c9d1d9] px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>
              ),
              a: ({ href, children }) => (
                <a href={href} className="text-[#58a6ff] hover:text-[#79c0ff] underline" target="_blank" rel="noopener noreferrer">{children}</a>
              ),
              ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
              li: ({ children }) => <li>{children}</li>,
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-[#30363d] pl-4 italic text-[#8b949e] my-2">{children}</blockquote>
              ),
              hr: () => <hr className="border-[#30363d] my-4" />,
            }}
          >
            {block.content}
          </ReactMarkdown>
        </div>
      );
  }
};

export const MessageContent: React.FC<MessageContentProps> = ({ content, agentType }) => {
  const { blocks } = parseMessageContent(content);

  if (blocks.length === 0) {
    return (
      <div className="text-[14px] text-[#e0e0e0] leading-relaxed prose prose-invert prose-sm max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => <h1 className="text-xl font-bold text-white mt-4 mb-2">{children}</h1>,
            h2: ({ children }) => <h2 className="text-lg font-bold text-white mt-3 mb-2">{children}</h2>,
            h3: ({ children }) => <h3 className="text-base font-bold text-white mt-2 mb-1">{children}</h3>,
            h4: ({ children }) => <h4 className="text-sm font-bold text-white mt-2 mb-1">{children}</h4>,
            p: ({ children }) => <p className="mb-2">{children}</p>,
            strong: ({ children }) => <strong className="font-bold text-white">{children}</strong>,
            em: ({ children }) => <em className="italic">{children}</em>,
            code: ({ children }) => (
              <code className="bg-[#0d1117] text-[#c9d1d9] px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>
            ),
            a: ({ href, children }) => (
              <a href={href} className="text-[#58a6ff] hover:text-[#79c0ff] underline" target="_blank" rel="noopener noreferrer">{children}</a>
            ),
            ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
            li: ({ children }) => <li>{children}</li>,
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-[#30363d] pl-4 italic text-[#8b949e] my-2">{children}</blockquote>
            ),
            hr: () => <hr className="border-[#30363d] my-4" />,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {blocks.map((block, index) => (
        <BlockRenderer key={index} block={block} agentType={agentType} />
      ))}
    </div>
  );
};

export default MessageContent;
