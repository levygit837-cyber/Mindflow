import { useState, useCallback } from 'react';
import { ChatLayout } from './components/chat/ChatLayout';
import { AgentCard } from './components/agents/AgentCard';
import { ChatView } from './components/chat/ChatView';
import { FolderPickerModal } from './components/input/FolderPickerModal';
import { useChatStream } from './hooks/useChatStream';
import { useChatStore } from './stores/chatStore';
import { AgentType } from './lib/constants';
import './styles/animations.css';

function App() {
  const [selectedAgent, setSelectedAgent] = useState<AgentType | null>(null);
  const [isOrchestrateMode, setIsOrchestrateMode] = useState(false);
  const [contextPaths] = useState<string[]>([]);
  const [folderPath, setFolderPath] = useState<string>('~');
  const [isFolderPickerOpen, setIsFolderPickerOpen] = useState(false);

  // Get messages from store
  const { messages, isStreaming, error } = useChatStore();

  // Initialize chat streaming hook
  const { sendMessage, stopStreaming } = useChatStream({
    agentType: selectedAgent || undefined,
    orchestrate: isOrchestrateMode,
    folderPath: folderPath,
  });

  // Handle sending messages
  const handleSend = useCallback(async (text: string) => {
    if (!text.trim() || isStreaming) return;
    await sendMessage(text);
  }, [sendMessage, isStreaming]);

  return (
    <>
      <ChatLayout
        folderPath={folderPath}
        selectedAgent={selectedAgent}
        contextPaths={contextPaths}
        isOrchestrateMode={isOrchestrateMode}
        onSend={handleSend}
        onSelectAgent={setSelectedAgent}
        onToggleOrchestrate={() => setIsOrchestrateMode(!isOrchestrateMode)}
        onFolderClick={() => setIsFolderPickerOpen(true)}
      >
        <div className="space-y-6">
          {/* Error Display */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Agent Selection Cards - only shown when no messages yet */}
          {messages.length === 0 && (
            <section>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-semibold text-[#707070] uppercase tracking-wider">
                  Select Agent
                </h3>
                {isStreaming && (
                  <button
                    onClick={stopStreaming}
                    className="text-xs text-red-400 hover:text-red-300 transition-colors"
                  >
                    Stop
                  </button>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <AgentCard
                  type="orchestrator"
                  isSelected={selectedAgent === 'orchestrator'}
                  onClick={() => setSelectedAgent('orchestrator')}
                />
                <AgentCard
                  type="analyst"
                  isSelected={selectedAgent === 'analyst'}
                  onClick={() => setSelectedAgent('analyst')}
                />
                <AgentCard
                  type="coder"
                  isSelected={selectedAgent === 'coder'}
                  onClick={() => setSelectedAgent('coder')}
                />
                <AgentCard
                  type="researcher"
                  isSelected={selectedAgent === 'researcher'}
                  onClick={() => setSelectedAgent('researcher')}
                />
              </div>
            </section>
          )}

          {/* Chat View - messages with inline events */}
          <ChatView />
        </div>
      </ChatLayout>

      {/* Folder Picker Modal */}
      <FolderPickerModal
        isOpen={isFolderPickerOpen}
        currentPath={folderPath}
        onSelect={(path) => setFolderPath(path)}
        onClose={() => setIsFolderPickerOpen(false)}
      />
    </>
  );
}

export default App;
