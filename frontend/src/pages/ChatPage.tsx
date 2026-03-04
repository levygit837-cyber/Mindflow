import React from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChatInterface } from '../components/ChatInterface';

export const ChatPage: React.FC = () => {
  const { sessionId } = useParams();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="h-full"
    >
      <ChatInterface sessionId={sessionId} />
    </motion.div>
  );
};
