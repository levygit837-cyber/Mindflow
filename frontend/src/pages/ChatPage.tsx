import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { ChatInterface } from '../components/ChatInterface';
import { TopBar } from '../components/Header/TopBar';

const AVAILABLE_MODELS = [
  'gemini-3.1-flash-lite-preview',
  'gemini-1.5-pro',
  'claude-sonnet-4-6',
  'claude-opus-4-6',
  'gpt-4o',
];

export const ChatPage: React.FC = () => {
  const { sessionId } = useParams();
  const [title, setTitle] = useState('New Chat');
  const [agentCount, setAgentCount] = useState(0);
  const [workflowType, setWorkflowType] = useState<'parallel' | 'sequential' | 'orchestrator' | 'chain'>('orchestrator');
  const [selectedModel, setSelectedModel] = useState('gemini-3.1-flash-lite-preview');

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar
        title={title}
        agentCount={agentCount}
        workflowType={workflowType}
        selectedModel={selectedModel}
        availableModels={AVAILABLE_MODELS}
        onModelChange={setSelectedModel}
      />
      <ChatInterface
        sessionId={sessionId}
        selectedModel={selectedModel}
        onTitleChange={setTitle}
        onAgentCountChange={setAgentCount}
        onWorkflowChange={setWorkflowType}
      />
    </div>
  );
};
