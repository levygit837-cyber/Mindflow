import React from 'react';
import { motion } from 'framer-motion';
import { Settings as SettingsIcon, Brain, Palette, Globe } from 'lucide-react';
import { Card } from '../components/common';
import { useSettings, useAppStore } from '../stores/appStore';

export const SettingsPage: React.FC = () => {
  const settings = useSettings();
  const { setSettings, setTheme } = useAppStore();

  const handleSettingChange = (key: string, value: any) => {
    setSettings({ [key]: value });
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
          Settings
        </h1>
        <p className="text-text-secondary">
          Customize your MindFlow experience
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Appearance Settings */}
        <Card elevation="md" padding="lg">
          <div className="flex items-center space-x-3 mb-4">
            <Palette className="h-5 w-5 text-brand-primary" />
            <h3 className="text-lg font-semibold text-text-primary">Appearance</h3>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Theme
              </label>
              <select
                value={settings.theme || 'dark'}
                onChange={(e) => setTheme(e.target.value as 'dark' | 'light')}
                className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text-primary"
              >
                <option value="dark">Dark</option>
                <option value="light">Light</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Font Size
              </label>
              <select
                value={settings.fontSize}
                onChange={(e) => handleSettingChange('fontSize', e.target.value)}
                className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text-primary"
              >
                <option value="small">Small</option>
                <option value="medium">Medium</option>
                <option value="large">Large</option>
              </select>
            </div>
          </div>
        </Card>

        {/* AI Settings */}
        <Card elevation="md" padding="lg">
          <div className="flex items-center space-x-3 mb-4">
            <Brain className="h-5 w-5 text-brand-primary" />
            <h3 className="text-lg font-semibold text-text-primary">AI Configuration</h3>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Provider
              </label>
              <select
                value={settings.provider}
                onChange={(e) => handleSettingChange('provider', e.target.value)}
                className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text-primary"
              >
                <option value="google">Google (Gemini)</option>
                <option value="openai">OpenAI (GPT)</option>
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Orchestration Mode
              </label>
              <select
                value={settings.orchestrationMode}
                onChange={(e) => handleSettingChange('orchestrationMode', e.target.value)}
                className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text-primary"
              >
                <option value="auto_route">Auto Route</option>
                <option value="single_agent">Single Agent</option>
                <option value="decomposition_thinking">Decomposition Thinking</option>
              </select>
            </div>
          </div>
        </Card>

        {/* Language Settings */}
        <Card elevation="md" padding="lg">
          <div className="flex items-center space-x-3 mb-4">
            <Globe className="h-5 w-5 text-brand-primary" />
            <h3 className="text-lg font-semibold text-text-primary">Language & Region</h3>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Language
              </label>
              <select
                value={settings.language}
                onChange={(e) => handleSettingChange('language', e.target.value)}
                className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text-primary"
              >
                <option value="en">English</option>
                <option value="pt">Português</option>
              </select>
            </div>
          </div>
        </Card>

        {/* Chat Settings */}
        <Card elevation="md" padding="lg">
          <div className="flex items-center space-x-3 mb-4">
            <SettingsIcon className="h-5 w-5 text-brand-primary" />
            <h3 className="text-lg font-semibold text-text-primary">Chat Preferences</h3>
          </div>
          
          <div className="space-y-4">
            <label className="flex items-center space-x-3">
              <input
                type="checkbox"
                checked={settings.autoSaveSessions}
                onChange={(e) => handleSettingChange('autoSaveSessions', e.target.checked)}
                className="w-4 h-4 text-brand-primary bg-surface border-border rounded focus:ring-brand-primary"
              />
              <span className="text-sm text-text-primary">Auto-save sessions</span>
            </label>

            <label className="flex items-center space-x-3">
              <input
                type="checkbox"
                checked={settings.showReasoning}
                onChange={(e) => handleSettingChange('showReasoning', e.target.checked)}
                className="w-4 h-4 text-brand-primary bg-surface border-border rounded focus:ring-brand-primary"
              />
              <span className="text-sm text-text-primary">Show reasoning process</span>
            </label>

            <label className="flex items-center space-x-3">
              <input
                type="checkbox"
                checked={settings.enableNotifications}
                onChange={(e) => handleSettingChange('enableNotifications', e.target.checked)}
                className="w-4 h-4 text-brand-primary bg-surface border-border rounded focus:ring-brand-primary"
              />
              <span className="text-sm text-text-primary">Enable notifications</span>
            </label>
          </div>
        </Card>
      </div>
    </motion.div>
  );
};
