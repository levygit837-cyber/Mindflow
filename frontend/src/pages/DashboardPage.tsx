import React from 'react';
import { motion } from 'framer-motion';
import { Brain, Users, MessageSquare, Activity } from 'lucide-react';
import { Card } from '../components/common';
import { useAgents, useSessions } from '../stores/appStore';

export const DashboardPage: React.FC = () => {
  const agents = useAgents();
  const sessions = useSessions();

  const stats = {
    totalAgents: agents.length,
    activeAgents: agents.filter(a => a.status === 'online').length,
    totalSessions: sessions.length,
    recentSessions: sessions.filter(s => {
      const sessionDate = new Date(s.updatedAt);
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      return sessionDate > weekAgo;
    }).length,
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary mb-2">
          Welcome to MindFlow
        </h1>
        <p className="text-text-secondary">
          Your multi-agent AI assistant system
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card elevation="md" padding="md">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-brand-primary/10 rounded-lg">
              <Brain className="h-6 w-6 text-brand-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">{stats.totalAgents}</p>
              <p className="text-sm text-text-secondary">Total Agents</p>
            </div>
          </div>
        </Card>

        <Card elevation="md" padding="md">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-state-success/10 rounded-lg">
              <Users className="h-6 w-6 text-state-success" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">{stats.activeAgents}</p>
              <p className="text-sm text-text-secondary">Active Agents</p>
            </div>
          </div>
        </Card>

        <Card elevation="md" padding="md">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-state-info/10 rounded-lg">
              <MessageSquare className="h-6 w-6 text-state-info" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">{stats.totalSessions}</p>
              <p className="text-sm text-text-secondary">Total Sessions</p>
            </div>
          </div>
        </Card>

        <Card elevation="md" padding="md">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-state-action/10 rounded-lg">
              <Activity className="h-6 w-6 text-state-action" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">{stats.recentSessions}</p>
              <p className="text-sm text-text-secondary">Recent Sessions</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card elevation="md" padding="lg" hover clickable>
          <h3 className="text-lg font-semibold text-text-primary mb-3">
            Start New Chat
          </h3>
          <p className="text-text-secondary mb-4">
            Begin a conversation with any of our specialized AI agents
          </p>
          <button className="w-full bg-gradient-to-r from-brand-primary to-brand-primary-light text-white py-2 px-4 rounded-lg hover:from-brand-primary-dark hover:to-brand-primary transition-all">
            Start Chatting
          </button>
        </Card>

        <Card elevation="md" padding="lg" hover clickable>
          <h3 className="text-lg font-semibold text-text-primary mb-3">
            View Agents
          </h3>
          <p className="text-text-secondary mb-4">
            Explore all available AI agents and their capabilities
          </p>
          <button className="w-full bg-surface-elevated text-text-primary py-2 px-4 rounded-lg hover:bg-surface transition-all border border-border">
            View All Agents
          </button>
        </Card>
      </div>
    </motion.div>
  );
};
