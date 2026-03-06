import React from 'react';
import { motion } from 'framer-motion';
import { MessageSquare, Send } from 'lucide-react';
import { Card, Input, Button } from '../common';
import { useMessages, useStreamingState } from '../../stores/appStore';

interface ChatInterfaceProps {
  sessionId?: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ sessionId: _sessionId }) => {
  const messages = useMessages();
  const { isStreaming } = useStreamingState();
  const [inputValue, setInputValue] = React.useState('');

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      // TODO: Implement message sending logic
      console.log('Sending message:', inputValue);
      setInputValue('');
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Messages Area */}
      <div className="flex-1 overflow-auto mb-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center"
            >
              <MessageSquare className="h-12 w-12 text-brand-primary mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-text-primary mb-2">
                Start a conversation
              </h3>
              <p className="text-text-secondary">
                Choose an agent and begin chatting with MindFlow
              </p>
            </motion.div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`flex ${
                  message.type === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <Card
                  elevation="sm"
                  padding="md"
                  className={`max-w-lg ${
                    message.type === 'user'
                      ? 'bg-brand-primary text-white'
                      : 'bg-surface-elevated'
                  }`}
                >
                  <div className="text-sm font-medium mb-1">
                    {message.type === 'user' ? 'You' : 'Assistant'}
                  </div>
                  <div className="whitespace-pre-wrap">
                    {message.content}
                  </div>
                </Card>
              </motion.div>
            ))}
            
            {isStreaming && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <Card elevation="sm" padding="md" className="bg-surface-elevated">
                  <div className="flex items-center space-x-2">
                    <div className="animate-pulse">Thinking...</div>
                  </div>
                </Card>
              </motion.div>
            )}
          </div>
        )}
      </div>

      {/* Input Area */}
      <Card elevation="md" padding="md">
        <div className="flex space-x-2">
          <Input
            value={inputValue}
            onChange={setInputValue}
            placeholder="Type your message..."
            className="flex-1"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isStreaming}
            loading={isStreaming}
            icon={<Send className="h-4 w-4" />}
          >
            Send
          </Button>
        </div>
      </Card>
    </div>
  );
};
