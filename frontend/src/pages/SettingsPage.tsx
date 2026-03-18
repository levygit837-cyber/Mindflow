import React from 'react';
import { motion } from 'framer-motion';
import { Card } from '../components/common';
import { useSettings, useAppStore } from '../stores/appStore';
import { normalizeProvider, resolveModelForProvider } from '../utils/llm';

const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 16px',
  background: 'color-mix(in srgb, var(--surface-glass) 68%, var(--surface) 32%)',
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
  const theme = useAppStore((state) => state.theme);
  const { setSettings } = useAppStore();

  const handleSettingChange = (key: string, value: unknown) => {
    if (key === 'provider' && typeof value === 'string') {
      const provider = normalizeProvider(value);
      setSettings({
        provider,
        model: resolveModelForProvider(provider, settings.model),
      });
      return;
    }

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
            fontFamily: 'var(--font-brand)',
            fontSize: 38,
            fontWeight: 500,
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
            <div className="space-y-2">
              <span style={{ color: 'var(--text-primary)', fontSize: 14, fontWeight: 500 }}>Tema</span>
              <div
                style={{
                  ...selectStyle,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <span>{theme === 'dark' ? 'Dark mode' : 'Light mode'}</span>
                <span className="mono-label">topbar toggle</span>
              </div>
            </div>

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
                value={normalizeProvider(settings.provider)}
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
