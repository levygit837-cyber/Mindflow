import {
  formatMindflowV2Duration,
  getMindflowV2AgentTheme,
  resolveMindflowV2AgentType,
  resolveMindflowV2Tone,
  summarizeMindflowV2Value,
  type MindflowV2AgentType,
  type MindflowV2Tone,
} from './mindflowV2';

export interface JourneyStep {
  id: string;
  title: string;
  detail: string;
  status: 'live' | 'done' | 'queued' | 'waiting' | 'error';
  agentType?: MindflowV2AgentType;
  meta?: string;
}

interface StreamLikeEvent {
  id?: string;
  type: string;
  data: string;
  meta?: Record<string, unknown> | null;
}

interface ParsedStreamToolEvent {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'error' | 'collapsed';
  args?: unknown;
  result?: unknown;
  error?: string;
  agentName?: string;
  elapsed?: string;
}

interface DelegationAgentRow {
  name: string;
  role: string;
  status: string;
  accent?: string;
  agentType?: MindflowV2AgentType;
}

interface ParsedStreamDelegation {
  id: string;
  title: string;
  subtitle?: string;
  status: string;
  pipeline?: string;
  summary?: string;
  agents: DelegationAgentRow[];
  variant?: 'simple' | 'rich';
  accent?: string;
}

interface ParsedStreamMemory {
  id: string;
  source: 'vector' | 'database';
  status: string;
  label?: string;
  count?: number;
  detail?: string;
  agentName?: string;
  done?: boolean;
}

interface ParsedStreamNotifier {
  id: string;
  title: string;
  status: string;
  message?: string;
  detail?: string;
  tone?: MindflowV2Tone;
}

interface ParsedStreamThought {
  id: string;
  agentType: MindflowV2AgentType;
  title?: string;
  status?: string;
  content: string;
  summary?: string;
  defaultExpanded?: boolean;
}

export interface ParsedStreamJourney {
  steps: JourneyStep[];
  activeStepId?: string;
  summary?: string;
}

export interface StreamError {
  id: string;
  message: string;
  code?: string;
  timestamp: number;
  recoverable: boolean;
}

export interface StreamDiagnostics {
  scopeEscape: boolean;
}

export interface StreamPresentation {
  activeAgents: MindflowV2AgentType[];
  thinkingStatuses: Partial<Record<MindflowV2AgentType, string>>;
  thoughts: ParsedStreamThought[];
  delegations: ParsedStreamDelegation[];
  toolEvents: ParsedStreamToolEvent[];
  notifiers: ParsedStreamNotifier[];
  memoryEvents: ParsedStreamMemory[];
  journey: ParsedStreamJourney;
  errors: StreamError[];
  diagnostics: StreamDiagnostics;
}

// Infra-level agent_step names that add noise without business value
const INFRA_STEP_PATTERNS = [
  /^__/,
  /_route$/i,
  /_check$/i,
  /^analyze[_\s]request$/i,
  /^orchestrat/i,
  /^direct[_\s]agent:/i,
  /^route[_\s]to/i,
  /^dispatch/i,
  /^initialize/i,
];

function isBusinessStep(label: string): boolean {
  return !INFRA_STEP_PATTERNS.some((p) => p.test(label));
}

const NOTIFIER_CAP = 6;

function normalizeText(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }

  return String(value).trim();
}

function parseObject(value: string): Record<string, unknown> | null {
  const trimmed = value.trim();
  if (!trimmed) return null;

  try {
    const parsed = JSON.parse(trimmed);
    return parsed && typeof parsed === 'object' ? parsed as Record<string, unknown> : null;
  } catch {
    return null;
  }
}

function titleCase(value: string) {
  return value
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function pluralize(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function coerceAgentType(raw: unknown, fallback: MindflowV2AgentType = 'orchestrator'): MindflowV2AgentType {
  if (typeof raw !== 'string' || !raw.trim()) {
    return fallback;
  }

  return resolveMindflowV2AgentType(raw);
}

function resolveAgentLabel(agentType: MindflowV2AgentType): string {
  return getMindflowV2AgentTheme(agentType).label;
}

export function parseStructuredStreamEventData(value: string): Record<string, unknown> | null {
  return parseObject(value);
}

export function buildStreamPresentation(events: StreamLikeEvent[], isStreaming = false): StreamPresentation {
  const activeAgents = new Set<MindflowV2AgentType>();
  const thinkingStatuses: Partial<Record<MindflowV2AgentType, string>> = {};
  const thoughts: ParsedStreamThought[] = [];
  const rawNotifiers: ParsedStreamNotifier[] = [];
  const memoryEvents: ParsedStreamMemory[] = [];
  const journeySteps: JourneyStep[] = [];
  const errors: StreamError[] = [];
  const delegations = new Map<string, ParsedStreamDelegation>();
  const toolEvents = new Map<string, ParsedStreamToolEvent>();
  let scopeEscape = false;

  // Dedup notifiers: key = `${title}:${status}`, value = last push timestamp (ms)
  const notifierSeen = new Map<string, number>();

  const addJourneyStep = (step: JourneyStep) => {
    journeySteps.push(step);
  };

  const pushNotifier = (n: ParsedStreamNotifier) => {
    const key = `${n.title}:${n.status}`;
    const last = notifierSeen.get(key) ?? 0;
    const now = Date.now();
    if (now - last < 2000) return; // deduplicate within 2s window
    notifierSeen.set(key, now);
    rawNotifiers.push(n);
  };

  for (const event of events) {
    const type = String(event.type ?? '').toLowerCase();
    const agentType = coerceAgentType(event.meta?.agent);

    // ── Orchestrator lifecycle ──────────────────────────────────────────────
    if (type === 'orchestrator_thinking_start') {
      activeAgents.add('orchestrator');
      thinkingStatuses.orchestrator = 'routing';
      // No notifier, no journey — just update the pill
      continue;
    }

    if (type === 'orchestrator_thinking' || type === 'thought') {
      const content = normalizeText(event.data);
      const thoughtAgent = normalizeText(event.meta?.agent) ? coerceAgentType(event.meta?.agent) : agentType;
      activeAgents.add(thoughtAgent);
      thoughts.push({
        id: event.id ?? `thought-${thoughts.length}`,
        agentType: thoughtAgent,
        title: resolveAgentLabel(thoughtAgent),
        status: event.meta?.category ? String(event.meta.category) : (type === 'orchestrator_thinking' ? 'thinking' : 'thought'),
        content,
        summary: event.meta?.nodeLabel ? String(event.meta.nodeLabel) : undefined,
        defaultExpanded: type === 'orchestrator_decision' || content.length < 300,
      });
      // No journey — thoughts live in the chat feed only
      continue;
    }

    if (type === 'orchestrator_decision') {
      const decision = parseObject(event.data);
      // Detect scope escape from decision payload
      if (
        decision?.scope_escape ||
        decision?.execution_strategy === 'scope_escape' ||
        String(decision?.routing_reason ?? '').toLowerCase().includes('scope') ||
        String(decision?.decision ?? '').toLowerCase().includes('out of scope')
      ) {
        scopeEscape = true;
      }
      thoughts.push({
        id: event.id ?? `decision-${thoughts.length}`,
        agentType: 'orchestrator',
        title: 'Decisão de roteamento',
        status: 'decision',
        content: summarizeMindflowV2Value(decision ?? event.data, 320),
        summary: 'Decisão da orquestração',
        defaultExpanded: true,
      });
      // No notifier, no journey — decision is visible as a ThoughtBlock
      continue;
    }

    if (type === 'orchestrator_thinking_end') {
      activeAgents.add('orchestrator');
      thinkingStatuses.orchestrator = 'ready';
      // No notifier, no journey
      continue;
    }

    if (type === 'reflection_mode_start') {
      addJourneyStep({
        id: event.id ?? `event-${journeySteps.length}`,
        title: 'Reflexão',
        detail: 'Fase de reflexão iniciada.',
        status: 'live',
        agentType: 'orchestrator',
        meta: 'reflection',
      });
      continue;
    }

    if (type === 'reflection_mode_end') {
      activeAgents.add('orchestrator');
      thinkingStatuses.orchestrator = 'ready';
      addJourneyStep({
        id: event.id ?? `event-${journeySteps.length}`,
        title: 'Reflexão concluída',
        detail: 'Fase de reflexão encerrada.',
        status: 'done',
        agentType: 'orchestrator',
        meta: 'reflection',
      });
      continue;
    }

    // ── Delegation ──────────────────────────────────────────────────────────
    if (type === 'agent_delegation_start' || type === 'specialist_activation') {
      const payload = parseObject(event.data) ?? {};
      const resolvedAgent = coerceAgentType(payload.agent_role ?? payload.agent_type ?? payload.agent ?? event.meta?.agent);
      const agentTheme = getMindflowV2AgentTheme(resolvedAgent);
      const key = String(payload.step_id ?? payload.agent_id ?? payload.specialist ?? event.id ?? `delegation-${delegations.size}`);
      activeAgents.add(resolvedAgent);

      const current = delegations.get(key) ?? {
        id: key,
        title: 'Delegation / orchestration',
        subtitle: '',
        status: 'ativo',
        pipeline: payload.step_id ? `Pipeline #${payload.step_id}` : undefined,
        summary: '',
        agents: [],
        variant: 'rich' as const,
        accent: agentTheme.accent,
      };

      current.subtitle = payload.task ? String(payload.task) : current.subtitle;
      current.summary = payload.task ? String(payload.task) : current.summary;
      current.status = type === 'specialist_activation' ? 'especialista ativo' : 'ativo';
      current.pipeline = payload.step_id ? `Pipeline #${payload.step_id}` : current.pipeline;
      current.agents = [
        ...current.agents.filter((item) => item.role !== agentTheme.label),
        {
          name: agentTheme.label,
          role: payload.delegated_by ? String(payload.delegated_by) : 'Delegated agent',
          status: type === 'specialist_activation' ? 'ativo' : 'delegado',
          accent: agentTheme.accent,
          agentType: resolvedAgent,
        },
      ];

      delegations.set(key, current);

      // Journey only for delegation_start (not specialist_activation — that's a pill update)
      if (type === 'agent_delegation_start') {
        addJourneyStep({
          id: key,
          title: `Delegado para ${agentTheme.label}`,
          detail: payload.task ? String(payload.task) : 'Delegação criada.',
          status: 'live',
          agentType: resolvedAgent,
          meta: payload.delegated_by ? `de ${payload.delegated_by}` : 'delegação',
        });
      }
      // No notifier — DelegationCard is the visual owner
      continue;
    }

    if (type === 'agent_delegation_complete') {
      const payload = parseObject(event.data) ?? {};
      const resolvedAgent = coerceAgentType(payload.agent_role ?? payload.agent_type ?? payload.agent ?? event.meta?.agent);
      activeAgents.add(resolvedAgent);
      addJourneyStep({
        id: event.id ?? `event-${journeySteps.length}`,
        title: 'Delegação concluída',
        detail: payload.task ? String(payload.task) : 'Tarefa delegada concluída.',
        status: 'done',
        agentType: resolvedAgent,
        meta: payload.agent_id ? String(payload.agent_id) : 'complete',
      });
      continue;
    }

    // ── Tool calls ──────────────────────────────────────────────────────────
    if (
      type === 'tool_call' ||
      type === 'tool_result' ||
      type === 'tool_operation_start' ||
      type === 'tool_operation_complete' ||
      type === 'tool_operation_update'
    ) {
      const payload = parseObject(event.data) ?? {};
      const toolId = String(payload.id ?? event.meta?.toolCallId ?? event.id ?? `tool-${toolEvents.size}`);
      const name = normalizeText(payload.name ?? event.meta?.nodeLabel ?? 'tool');
      const args = payload.args ?? payload.parameters ?? payload.tool_meta ?? payload;
      const result = payload.result ?? payload.output ?? payload.result_preview;
      const toolError = normalizeText(payload.error ?? payload.message ?? '');
      const agentName = normalizeText(event.meta?.agent);
      const current = toolEvents.get(toolId) ?? {
        id: toolId,
        name,
        status: 'running' as const,
        args,
        result: undefined,
        error: undefined,
        agentName: agentName || undefined,
        elapsed: undefined,
      };

      current.name = name || current.name;
      current.args = args ?? current.args;
      current.agentName = agentName || current.agentName;

      if (type === 'tool_call' || type === 'tool_operation_start' || type === 'tool_operation_update') {
        current.status = 'running';
      }

      if (type === 'tool_result' || type === 'tool_operation_complete') {
        current.status = payload.error ? 'error' : 'completed';
        current.result = result ?? current.result;
        current.error = toolError || current.error;
      }

      toolEvents.set(toolId, current);
      activeAgents.add(coerceAgentType(event.meta?.agent));
      // No journey — ToolEventCard is the visual owner
      continue;
    }

    // ── Agent steps (filtered) ──────────────────────────────────────────────
    if (type === 'agent_step' || type === 'step') {
      const payload = parseObject(event.data) ?? {};
      const label = normalizeText(payload.stepName ?? event.meta?.nodeLabel ?? event.meta?.node ?? 'Step');
      const action = normalizeText(payload.action ?? event.meta?.status ?? 'update');
      const currentAgent = coerceAgentType(event.meta?.agent);

      activeAgents.add(currentAgent);

      if (!isBusinessStep(label)) continue; // drop infra noise

      addJourneyStep({
        id: event.id ?? `step-${journeySteps.length}`,
        title: label,
        detail: normalizeText(payload.detail ?? payload.message ?? event.data) || action,
        status: action === 'complete' ? 'done' : 'live',
        agentType: currentAgent,
        meta: action,
      });
      continue;
    }

    // ── Notifiers ───────────────────────────────────────────────────────────
    if (type === 'notifier') {
      const payload = parseObject(event.data) ?? {};
      const kind = normalizeText(payload.kind ?? payload.category ?? event.meta?.category ?? event.meta?.nodeCategory);
      const message = normalizeText(payload.message ?? event.data);
      const details = payload.details && typeof payload.details === 'object'
        ? (payload.details as Record<string, unknown>)
        : {};
      const tone = resolveMindflowV2Tone(kind);

      if (kind === 'context_loaded' || kind.includes('memory')) {
        const sourceRaw = normalizeText(details.source ?? payload.source ?? event.meta?.agent);
        const source = sourceRaw.toLowerCase().includes('database') || sourceRaw.toLowerCase().includes('session')
          ? 'database'
          : 'vector';
        const count = typeof details.count === 'number' ? details.count : typeof payload.count === 'number' ? payload.count : undefined;
        memoryEvents.push({
          id: event.id ?? `memory-${memoryEvents.length}`,
          source,
          status: message || 'contexto carregado',
          label: source === 'database' ? 'Database Memory Recall' : 'Vector Memory Recall',
          count,
          detail: count ? `${count} ${source === 'database' ? 'registros' : 'fragmentos'} recuperados` : message || undefined,
          agentName: sourceRaw || undefined,
          done: true,
        });
        activeAgents.add('researcher');
        continue;
      }

      pushNotifier({
        id: event.id ?? `notifier-${rawNotifiers.length}`,
        title: kind ? titleCase(kind.replace(/_/g, ' ')) : 'Run',
        status: message || kind || 'info',
        message: Object.keys(details).length > 0 ? message || summarizeMindflowV2Value(details, 180) : message,
        detail: Object.keys(details).length > 0 ? summarizeMindflowV2Value(details, 180) : undefined,
        tone,
      });
      continue;
    }

    // ── Execution start ─────────────────────────────────────────────────────
    if (type === 'agent_execution_start') {
      const payload = parseObject(event.data) ?? {};
      activeAgents.add(agentType);
      addJourneyStep({
        id: event.id ?? `exec-start-${journeySteps.length}`,
        title: 'Execução iniciada',
        detail: normalizeText(payload.execution_id ?? payload.root_execution_id ?? 'execução'),
        status: 'live',
        agentType,
        meta: normalizeText(payload.stage ?? payload.status ?? 'running'),
      });
      continue;
    }

    // ── Error ───────────────────────────────────────────────────────────────
    if (type === 'error') {
      const payload = parseObject(event.data) ?? {};
      const message = normalizeText(payload.message ?? payload.error ?? event.data ?? 'Erro desconhecido');
      errors.push({
        id: event.id ?? `error-${errors.length}`,
        message,
        code: payload.code ? String(payload.code) : undefined,
        timestamp: Date.now(),
        recoverable: Boolean(payload.recoverable ?? false),
      });
      addJourneyStep({
        id: event.id ?? `error-step-${journeySteps.length}`,
        title: 'Erro',
        detail: message,
        status: 'error',
        agentType,
        meta: payload.code ? String(payload.code) : 'error',
      });
      continue;
    }
  }

  if (isStreaming && activeAgents.size === 0) {
    activeAgents.add('orchestrator');
  }

  const orderedDelegations = Array.from(delegations.values());
  const orderedTools = Array.from(toolEvents.values());
  const activeLiveStep = [...journeySteps].reverse().find((step) => step.status === 'live');
  const activeStepId = activeLiveStep?.id ?? journeySteps[journeySteps.length - 1]?.id;
  const summary = [
    pluralize(journeySteps.length, 'etapa', 'etapas'),
    pluralize(activeAgents.size, 'agente', 'agentes'),
    orderedTools.length > 0 ? pluralize(orderedTools.length, 'ferramenta', 'ferramentas') : null,
  ]
    .filter(Boolean)
    .join(' · ');

  // Apply cap: keep only the most recent NOTIFIER_CAP notifiers
  const notifiers = rawNotifiers.slice(-NOTIFIER_CAP);

  return {
    activeAgents: Array.from(activeAgents),
    thinkingStatuses,
    thoughts,
    delegations: orderedDelegations,
    toolEvents: orderedTools,
    notifiers,
    memoryEvents,
    journey: {
      steps: journeySteps,
      activeStepId,
      summary,
    },
    errors,
    diagnostics: { scopeEscape },
  };
}

export function getMindflowV2ElapsedLabel(startedAt?: Date | null): string | undefined {
  if (!startedAt) return undefined;

  return `ao vivo · ${formatMindflowV2Duration(Date.now() - startedAt.getTime())}`;
}
