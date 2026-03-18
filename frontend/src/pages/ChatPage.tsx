import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ChatInterface } from '../components/ChatInterface';
import { TopBar } from '../components/Header/TopBar';
import { useAppStore, useSettings } from '../stores/appStore';
import { getModelsForProvider, normalizeProvider, resolveModelForProvider } from '../utils/llm';

export const ChatPage: React.FC = () => {
  const { sessionId } = useParams();
  const [title, setTitle] = useState('New Chat');
  const [agentCount, setAgentCount] = useState(0);
  const [workflowType, setWorkflowType] = useState<'parallel' | 'sequential' | 'orchestrator' | 'chain'>('orchestrator');
  const settings = useSettings();
  const setSettings = useAppStore((state) => state.setSettings);
  const selectedProvider = normalizeProvider(settings.provider);
  const selectedModel = resolveModelForProvider(selectedProvider, settings.model);
  const availableModels = useMemo(
    () => getModelsForProvider(selectedProvider),
    [selectedProvider],
  );

  useEffect(() => {
    if (settings.provider !== selectedProvider || settings.model !== selectedModel) {
      setSettings({
        provider: selectedProvider,
        model: selectedModel,
      });
    }
  }, [selectedModel, selectedProvider, setSettings, settings.model, settings.provider]);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <TopBar
        title={title}
        agentCount={agentCount}
        workflowType={workflowType}
        selectedModel={selectedModel}
        availableModels={availableModels}
        onModelChange={(model) => setSettings({ model })}
      />
      <ChatInterface
        key={sessionId ?? 'new'}
        sessionId={sessionId}
        selectedProvider={selectedProvider}
        selectedModel={selectedModel}
        onTitleChange={setTitle}
        onAgentCountChange={setAgentCount}
        onWorkflowChange={setWorkflowType}
      />
    </div>
  );
};
