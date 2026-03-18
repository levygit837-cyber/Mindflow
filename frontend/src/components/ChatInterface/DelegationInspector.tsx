import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, Brain, CheckCircle2, ChevronRight, Clock3, Search, Terminal, Wrench } from 'lucide-react';

type AgentType = 'orchestrator' | 'coder' | 'analyst' | 'researcher' | 'default';

type InspectorStatus = 'live' | 'done' | 'queued' | 'waiting' | 'error';

type InspectorSourceMessage =
  | {
      id: string;
      role: 'thought';
      agentType: AgentType;
      agentName: string;
      content: string;
    }
  | {
      id: string;
      role: 'agent';
      agentType: AgentType;
      agentName: string;
      content: string;
    }
  | {
      id: string;
      role: 'tool_call';
      agentType?: AgentType;
      agentName?: string;
      toolCall: {
        id: string;
        name: string;
        status: 'calling' | 'success' | 'error';
      };
    }
  | {
      id: string;
      role: 'stream_notifier';
      title: string;
      status: string;
      detail?: string;
      tone: 'accent' | 'info' | 'success' | 'warning' | 'error' | 'neutral';
      active?: boolean;
      agentType?: AgentType;
      agentName?: string;
    }
  | {
      id: string;
      role: 'delegation';
      title: string;
      subtitle: string;
      agents: Array<{
        agentType: 'orchestrator' | 'analyst' | 'coder' | 'researcher';
        agentName: string;
        status: 'active' | 'pending' | 'done' | 'waiting';
      }>;
      pipelineLabel: string;
    }
  | {
      id: string;
      role: 'simple_delegation';
      agentType: AgentType;
      agentName: string;
      task: string;
    };

interface DelegationInspectorProps {
  items: InspectorSourceMessage[];
  className?: string;
}

interface InspectorStep {
  id: string;
  kind: 'thinking' | 'tool' | 'response' | 'status';
  title: string;
  detail: string;
  status: InspectorStatus;
}

interface DelegatedAgentTrail {
  id: string;
  agentType: AgentType;
  agentName: string;
  status: InspectorStatus;
  meta: string;
  steps: InspectorStep[];
}

function normalizeStatus(
  value: string | undefined | null,
  fallback: InspectorStatus = 'waiting',
): InspectorStatus {
  const normalized = String(value ?? '').toLowerCase();
  if (['live', 'active', 'running', 'calling'].includes(normalized)) return 'live';
  if (['done', 'completed', 'success', 'ready'].includes(normalized)) return 'done';
  if (['queued', 'pending'].includes(normalized)) return 'queued';
  if (['waiting', 'idle'].includes(normalized)) return 'waiting';
  if (['error', 'failed', 'failure'].includes(normalized)) return 'error';
  return fallback;
}

function statusLabel(status: InspectorStatus, steps: number) {
  switch (status) {
    case 'live':
      return `selected · ${steps} ações · live trail`;
    case 'done':
      return `done · ${steps} ações`;
    case 'queued':
      return `queued · ${steps} ações`;
    case 'error':
      return `error · ${steps} ações`;
    default:
      return `waiting · ${steps} ações`;
  }
}

function stepIcon(kind: InspectorStep['kind']) {
  switch (kind) {
    case 'thinking':
      return <Brain size={14} />;
    case 'tool':
      return <Wrench size={14} />;
    case 'response':
      return <CheckCircle2 size={14} />;
    default:
      return <Clock3 size={14} />;
  }
}

function agentGlyph(agentType: AgentType) {
  switch (agentType) {
    case 'researcher':
      return <Search size={14} />;
    case 'coder':
      return <Terminal size={14} />;
    case 'analyst':
      return <Brain size={14} />;
    default:
      return <Bot size={14} />;
  }
}

function buildDelegatedAgentTrails(items: InspectorSourceMessage[]) {
  const trails = new Map<string, DelegatedAgentTrail>();
  const order: string[] = [];

  const ensureTrail = (agentType: AgentType, agentName: string, status: InspectorStatus = 'waiting') => {
    const key = `${agentType}:${agentName}`;
    if (!trails.has(key)) {
      trails.set(key, {
        id: key,
        agentType,
        agentName,
        status,
        meta: statusLabel(status, 0),
        steps: [],
      });
      order.push(key);
    }

    const trail = trails.get(key)!;
    if (trail.status === 'waiting' && status !== 'waiting') {
      trail.status = status;
    }
    return trail;
  };

  items.forEach((item) => {
    if (item.role === 'delegation') {
      item.agents
        .filter((agent) => agent.agentType !== 'orchestrator')
        .forEach((agent) => {
          const trail = ensureTrail(
            agent.agentType,
            agent.agentName,
            normalizeStatus(agent.status, 'queued'),
          );
          trail.steps.push({
            id: `${item.id}:${agent.agentName}`,
            kind: 'status',
            title: 'Delegation started',
            detail: item.subtitle,
            status: normalizeStatus(agent.status, 'queued'),
          });
        });
      return;
    }

    if (item.role === 'simple_delegation' && item.agentType !== 'orchestrator') {
      const trail = ensureTrail(item.agentType, item.agentName, 'queued');
      if (trail.status === 'waiting') {
        trail.status = 'queued';
      }
      trail.steps.push({
        id: item.id,
        kind: 'status',
        title: 'Handoff prepared',
        detail: item.task,
        status: 'queued',
      });
      return;
    }

    if (item.role === 'thought' && item.agentType !== 'orchestrator') {
      const trail = ensureTrail(item.agentType, item.agentName, 'live');
      trail.status = 'live';
      trail.steps.push({
        id: item.id,
        kind: 'thinking',
        title: 'Thinking',
        detail: item.content,
        status: 'live',
      });
      return;
    }

    if (item.role === 'tool_call' && item.agentType && item.agentType !== 'orchestrator') {
      const toolStatus = normalizeStatus(item.toolCall.status, 'live');
      const trail = ensureTrail(item.agentType, item.agentName ?? 'Specialist', toolStatus);
      trail.status = toolStatus === 'error' ? 'error' : trail.status === 'done' ? 'done' : 'live';
      trail.steps.push({
        id: item.id,
        kind: 'tool',
        title: item.toolCall.name,
        detail: item.toolCall.status === 'calling' ? 'tool em execução' : `tool ${item.toolCall.status}`,
        status: toolStatus,
      });
      return;
    }

    if (item.role === 'agent' && item.agentType !== 'orchestrator') {
      const trail = ensureTrail(item.agentType, item.agentName, 'done');
      trail.status = 'done';
      trail.steps.push({
        id: item.id,
        kind: 'response',
        title: 'Response ready',
        detail: item.content,
        status: 'done',
      });
      return;
    }

    if (item.role === 'stream_notifier' && item.agentType && item.agentType !== 'orchestrator') {
      const notifierStatus = item.active
        ? 'live'
        : normalizeStatus(item.tone === 'error' ? 'error' : item.status, 'done');
      const trail = ensureTrail(item.agentType, item.agentName ?? item.title, notifierStatus);
      trail.status = notifierStatus;
      trail.steps.push({
        id: item.id,
        kind: 'status',
        title: item.title,
        detail: item.detail ?? item.status,
        status: notifierStatus,
      });
    }
  });

  const builtTrails = order
    .map((key) => trails.get(key))
    .filter((trail): trail is DelegatedAgentTrail => Boolean(trail))
    .map((trail) => ({
      ...trail,
      meta: statusLabel(trail.status, trail.steps.length),
    }));

  return builtTrails;
}

export const DelegationInspector: React.FC<DelegationInspectorProps> = ({
  items,
  className = '',
}) => {
  const trails = useMemo(() => buildDelegatedAgentTrails(items), [items]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (trails.length === 0) {
      setSelectedId(null);
      return;
    }

    setSelectedId((current) => {
      if (current && trails.some((trail) => trail.id === current)) return current;
      const liveTrail = [...trails].reverse().find((trail) => trail.status === 'live');
      return liveTrail?.id ?? trails[0]?.id ?? null;
    });
  }, [trails]);

  const selectedTrail = trails.find((trail) => trail.id === selectedId) ?? trails[0] ?? null;

  if (trails.length === 0 || !selectedTrail) {
    return null;
  }

  const stackedBackdrops = trails.slice(0, 2);

  return (
    <section className={`delegation-inspector-shell ${className}`}>
      <div className="delegation-inspector-header">
        <div className="mono-label">view mode · delegated agents</div>
        <h3 className="delegation-inspector-title">
          Open delegated agents in a stacked side panel
        </h3>
        <p className="delegation-inspector-subtitle">
          Each selection reveals one agent on the right and keeps the delegation trail visible as an ordered stack.
        </p>
      </div>

      <div className="delegation-inspector-body">
        <div className="delegation-inspector-rail">
          <div className="mono-label">delegated agents</div>
          <div className="delegation-inspector-rail-list">
            {trails.map((trail) => {
              const selected = trail.id === selectedTrail.id;
              return (
                <button
                  key={trail.id}
                  type="button"
                  className={`delegation-rail-card ${selected ? 'is-selected' : ''}`}
                  onClick={() => setSelectedId(trail.id)}
                >
                  <div className="delegation-rail-card-title">{trail.agentName}</div>
                  <div className="delegation-rail-card-meta">{selected ? statusLabel('live', trail.steps.length) : trail.meta}</div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="delegation-inspector-stage">
          {stackedBackdrops.map((trail, index) => (
            <div
              key={`backdrop-${trail.id}`}
              className={`delegation-stage-backdrop delegation-stage-backdrop-${index + 1}`}
              aria-hidden="true"
            />
          ))}

          <motion.div
            key={selectedTrail.id}
            className="delegation-stage-front"
            initial={{ opacity: 0, y: 8, x: 8 }}
            animate={{ opacity: 1, y: 0, x: 0 }}
            transition={{ duration: 0.24, ease: 'easeOut' }}
          >
            <div className="delegation-stage-front-header">
              <div className="delegation-stage-front-agent">
                <span className={`delegation-agent-glyph delegation-agent-glyph--${selectedTrail.agentType}`}>
                  {agentGlyph(selectedTrail.agentType)}
                </span>
                <div>
                  <div className="delegation-stage-front-label">{selectedTrail.agentName}</div>
                  <div className="delegation-stage-front-meta">{selectedTrail.meta}</div>
                </div>
              </div>

              <span className={`delegation-stage-status delegation-stage-status--${selectedTrail.status}`}>
                {selectedTrail.status}
              </span>
            </div>

            <div className="delegation-stage-legend">
              <span className="mono-label">trail</span>
              <span className="mono-label">{selectedTrail.steps.length} steps</span>
            </div>

            <div className="delegation-stage-steps">
              {selectedTrail.steps.map((step, index) => (
                <div key={step.id} className="delegation-step">
                  <div className="delegation-step-rail">
                    <span className={`delegation-step-dot delegation-step-dot--${step.status}`}>
                      {stepIcon(step.kind)}
                    </span>
                    {index < selectedTrail.steps.length - 1 ? <span className="delegation-step-line" /> : null}
                  </div>

                  <div className="delegation-step-content">
                    <div className="delegation-step-header">
                      <span className="delegation-step-title">{step.title}</span>
                      <span className="delegation-step-meta">{step.status}</span>
                    </div>
                    <p className="delegation-step-detail">{step.detail}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="delegation-stage-footer">
              <span className="mono-label">selected run</span>
              <span className="delegation-stage-footer-copy">
                keep the delegation trail visible as an ordered stack
              </span>
              <ChevronRight size={14} />
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

export default DelegationInspector;
