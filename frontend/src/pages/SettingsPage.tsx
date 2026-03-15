import React from 'react';
import { motion } from 'framer-motion';
import { Card } from '../components/common';
import { useSettings, useAppStore } from '../stores/appStore';

const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 16px',
  background: 'rgba(255, 255, 255, 0.02)',
  border: '1px solid var(--line-primary)',
  borderRadius: 16,
  color: 'var(--text-primary)',
  fontSize: 14,
  outline: 'none',
};

const checkboxRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
  padding: '12px 0',
  color: 'var(--text-secondary)',
};

export const SettingsPage: React.FC = () => {
  const settings = useSettings();
  const { setSettings, setTheme } = useAppStore();

  const handleSettingChange = (key: string, value: unknown) => {
    setSettings({ [key]: value });
  };

  return (
    <motion.div
      className="page-shell space-y-6"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
    >
      <div className="space-y-3">
        <div className="mono-label">settings / system rails</div>
        <h1
          style={{
            color: 'var(--text-primary)',
            fontSize: 32,
            fontWeight: 600,
            letterSpacing: '-0.04em',
          }}
        >
          Configuração mínima
        </h1>
        <p style={{ color: 'var(--text-secondary)', maxWidth: 620, lineHeight: 1.7 }}>
          Tipografia mais simples, menos ornamento e sinais objetivos. As preferências seguem a mesma linguagem do chat.
        </p>
      </div>

      <div className="page-grid lg:grid-cols-2">
        <Card padding="lg">
          <div className="mono-label mb-4">appearance</div>
          <div className="space-y-4">
            <label className="space-y-2 block">
              <span style={{ color: 'var(--text-primary)', fontSize: 14, fontWeight: 500 }}>Tema</span>
              <select
                value={settings.theme || 'dark'}
                onChange={(event) => setTheme(event.target.value as 'dark' | 'light')}
                style={selectStyle}
              >
                <option value="dark">Escuro</option>
                <option value="light">Claro</option>
              </select>
            </label>

            <label className="space-y-2 block">
              <span style={{ color: 'var(--text-primary)', fontSize: 14, fontWeight: 500 }}>Tamanho da fonte</span>
              <select
                value={settings.fontSize}
                onChange={(event) => handleSettingChange('fontSize', event.target.value)}
                style={selectStyle}
              >
                <option value="small">Pequena</option>
                <option value="medium">Média</option>
                <option value="large">Grande</option>
              </select>
            </label>
          </div>
        </Card>

        <Card padding="lg">
          <div className="mono-label mb-4">provider</div>
          <div className="space-y-4">
            <label className="space-y-2 block">
              <span style={{ color: 'var(--text-primary)', fontSize: 14, fontWeight: 500 }}>Provedor</span>
              <select
                value={settings.provider}
                onChange={(event) => handleSettingChange('provider', event.target.value)}
                style={selectStyle}
              >
                <option value="google">Google / Gemini</option>
                <option value="openai">OpenAI / GPT</option>
                <option value="anthropic">Anthropic / Claude</option>
                <option value="ollama">Ollama / Local</option>
              </select>
            </label>

            <label className="space-y-2 block">
              <span style={{ color: 'var(--text-primary)', fontSize: 14, fontWeight: 500 }}>Modo de orquestração</span>
              <select
                value={settings.orchestrationMode}
                onChange={(event) => handleSettingChange('orchestrationMode', event.target.value)}
                style={selectStyle}
              >
                <option value="auto_route">Auto route</option>
                <option value="single_agent">Single agent</option>
                <option value="decomposition_thinking">Decomposition thinking</option>
              </select>
            </label>
          </div>
        </Card>

        <Card padding="lg">
          <div className="mono-label mb-4">language</div>
          <label className="space-y-2 block">
            <span style={{ color: 'var(--text-primary)', fontSize: 14, fontWeight: 500 }}>Idioma</span>
            <select
              value={settings.language}
              onChange={(event) => handleSettingChange('language', event.target.value)}
              style={selectStyle}
            >
              <option value="en">English</option>
              <option value="pt">Português</option>
            </select>
          </label>
        </Card>

        <Card padding="lg">
          <div className="mono-label mb-4">chat</div>
          <div>
            <label style={checkboxRowStyle}>
              <input
                type="checkbox"
                checked={settings.autoSaveSessions}
                onChange={(event) => handleSettingChange('autoSaveSessions', event.target.checked)}
              />
              <span>Salvar sessões automaticamente</span>
            </label>

            <label style={checkboxRowStyle}>
              <input
                type="checkbox"
                checked={settings.showReasoning}
                onChange={(event) => handleSettingChange('showReasoning', event.target.checked)}
              />
              <span>Mostrar trilha de raciocínio</span>
            </label>

            <label style={checkboxRowStyle}>
              <input
                type="checkbox"
                checked={settings.enableNotifications}
                onChange={(event) => handleSettingChange('enableNotifications', event.target.checked)}
              />
              <span>Ativar notifiers</span>
            </label>
          </div>
        </Card>
      </div>
    </motion.div>
  );
};
