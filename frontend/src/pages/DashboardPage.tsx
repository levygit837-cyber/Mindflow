import React from 'react';
import { motion } from 'framer-motion';
import { Card } from '../components/common';
import { useAgents, useSessions } from '../stores/appStore';

export const DashboardPage: React.FC = () => {
  const agents = useAgents();
  const sessions = useSessions();

  const stats = [
    { label: 'agentes totais', value: agents.length, detail: 'mapa de especialistas disponíveis' },
    { label: 'agentes ativos', value: agents.filter((agent) => agent.status === 'online').length, detail: 'sinais simultâneos em execução' },
    { label: 'sessões', value: sessions.length, detail: 'histórico persistido no trilho' },
    {
      label: 'sessões recentes',
      value: sessions.filter((session) => {
        const sessionDate = new Date(session.updatedAt);
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        return sessionDate > weekAgo;
      }).length,
      detail: 'atividade dos últimos 7 dias',
    },
  ];

  return (
    <motion.div
      className="page-shell space-y-6"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
    >
      <div className="space-y-3">
        <div className="mono-label">overview / minimal rail</div>
        <h1
          style={{
            color: 'var(--text-primary)',
            fontSize: 32,
            fontWeight: 600,
            letterSpacing: '-0.04em',
          }}
        >
          Painel de coordenação
        </h1>
        <p style={{ color: 'var(--text-secondary)', maxWidth: 620, lineHeight: 1.7 }}>
          O dashboard agora segue a mesma lógica do chat: menos cor, mais direção. Cada número existe como um ponto de controle na trilha.
        </p>
      </div>

      <div className="page-grid md:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label} padding="lg" hover>
            <div className="mono-label mb-3">{stat.label}</div>
            <div
              style={{
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: 34,
                lineHeight: 1,
              }}
            >
              {stat.value}
            </div>
            <p style={{ marginTop: 14, color: 'var(--text-meta)', fontSize: 13, lineHeight: 1.6 }}>
              {stat.detail}
            </p>
          </Card>
        ))}
      </div>

      <div className="page-grid lg:grid-cols-2">
        <Card padding="lg" hover clickable>
          <div className="mono-label mb-3">quick start</div>
          <h2 style={{ color: 'var(--text-primary)', fontSize: 18, fontWeight: 600 }}>
            Abrir novo chat
          </h2>
          <p style={{ marginTop: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            Inicia um novo fluxo de delegação com o orchestrator no centro e notifiers visíveis.
          </p>
          <div className="mt-6 mono-chip" style={{ width: 'fit-content' }}>
            iniciar
          </div>
        </Card>

        <Card padding="lg" hover clickable>
          <div className="mono-label mb-3">audit</div>
          <h2 style={{ color: 'var(--text-primary)', fontSize: 18, fontWeight: 600 }}>
            Revisar agentes
          </h2>
          <p style={{ marginTop: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            Usa a mesma linguagem mínima do restante da interface para identificar gargalos e agentes disponíveis.
          </p>
          <div className="mt-6 mono-chip" style={{ width: 'fit-content' }}>
            mapear
          </div>
        </Card>
      </div>
    </motion.div>
  );
};
