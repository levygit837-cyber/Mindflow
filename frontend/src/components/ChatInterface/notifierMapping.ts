import type { StreamNotifierTone } from '../common/StreamNotifier';

export interface MappedNotifierPayload {
  title: string;
  status: string;
  detail?: string;
  tone: StreamNotifierTone;
  active?: boolean;
}

function humanizeNotifierDetail(
  message: string | undefined,
  details: Record<string, unknown> = {},
) {
  if (message?.trim()) return message.trim();

  const detailParts = Object.entries(details)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${String(value)}`);

  return detailParts.length > 0 ? detailParts.join(' · ') : undefined;
}

export function mapNotifierPayload(eventData: string): MappedNotifierPayload | null {
  let payload: {
    kind?: string;
    category?: string;
    message?: string;
    details?: Record<string, unknown>;
  } | null = null;

  try {
    payload = JSON.parse(eventData);
  } catch {
    return null;
  }

  if (!payload) return null;

  const kind = String(payload.kind ?? payload.category ?? '').toLowerCase();
  const details = payload.details ?? {};
  const detail = humanizeNotifierDetail(payload.message, details);

  if (kind === 'context_loaded') {
    return {
      title: 'Context',
      status: 'referências carregadas',
      detail,
      tone: 'info',
      active: false,
    };
  }

  if (kind === 'gitnexus_status') {
    return {
      title: 'GitNexus',
      status: 'verificando índice',
      detail,
      tone: 'accent',
      active: true,
    };
  }

  if (kind === 'gitnexus_query') {
    return {
      title: 'GitNexus',
      status: 'analisando fluxos',
      detail,
      tone: 'accent',
      active: true,
    };
  }

  if (kind === 'gitnexus_context') {
    return {
      title: 'GitNexus',
      status: 'carregando contexto',
      detail,
      tone: 'accent',
      active: true,
    };
  }

  if (kind === 'gitnexus_impact') {
    return {
      title: 'GitNexus',
      status: 'calculando impacto',
      detail,
      tone: 'warning',
      active: true,
    };
  }

  if (kind.startsWith('file_')) {
    const fileStatus: Record<string, string> = {
      file_read: 'lendo arquivo',
      file_write: 'escrevendo arquivo',
      file_edit: 'editando arquivo',
    };

    return {
      title: 'Filesystem',
      status: fileStatus[kind] ?? 'executando operação',
      detail,
      tone: 'info',
      active: true,
    };
  }

  if (kind.startsWith('shell_')) {
    const shellStatus: Record<string, string> = {
      shell_tab_open: 'abrindo shell',
      shell_tab_exec: 'executando shell',
      shell_tab_status: 'consultando shell',
      shell_tab_close: 'encerrando shell',
    };

    return {
      title: 'Runtime',
      status: shellStatus[kind] ?? 'atividade de shell',
      detail,
      tone: 'accent',
      active: true,
    };
  }

  if (kind === 'search_done') {
    return {
      title: 'Web',
      status: 'consultando fontes',
      detail,
      tone: 'info',
      active: true,
    };
  }

  if (kind === 'tool_start') {
    return {
      title: 'Tool',
      status: 'executando',
      detail,
      tone: 'accent',
      active: true,
    };
  }

  if (kind.includes('scope')) {
    return {
      title: 'Scope',
      status: 'fora do escopo',
      detail,
      tone: 'warning',
      active: false,
    };
  }

  if (kind.includes('slow') || kind.includes('performance')) {
    return {
      title: 'Performance',
      status: 'execução lenta',
      detail,
      tone: 'warning',
      active: false,
    };
  }

  if (kind.includes('error') || kind.includes('failed')) {
    return {
      title: 'Run',
      status: 'falha de execução',
      detail,
      tone: 'error',
      active: false,
    };
  }

  return {
    title: 'Run',
    status: payload.message?.trim() || kind || 'atualização',
    detail: detail === payload.message?.trim() ? undefined : detail,
    tone: 'neutral',
    active: false,
  };
}
