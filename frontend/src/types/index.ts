export interface Agent {
  id: AgentType;
  name: string;
  description: string;
  icon: string;
  color: string;
  capabilities: AgentCapabilities;
  status: AgentStatus;
  stats?: AgentStats;
}

export type AgentType = 
  | 'coder'
  | 'analyst' 
  | 'researcher'
  | 'arch_tech'
  | 'critic'
  | 'creative'
  | 'security_guard';

export interface AgentCapabilities {
  tools: string[];
  sandbox: SandboxMode;
  thinkingLevel: ThinkingLevel;
  keepContext: boolean;
}

export type SandboxMode = 'NONE' | 'READ_ONLY' | 'FULL';
export type ThinkingLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export type AgentStatus = 
  | 'online'
  | 'thinking'
  | 'busy'
  | 'offline'
  | 'error';

export interface AgentStats {
  successRate: number;
  avgResponseTime: number;
  totalTasks: number;
  lastActive: string;
}

export interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  agentType?: AgentType;
  timestamp: string;
  metadata?: MessageMetadata;
  reactions?: MessageReaction[];
}

export interface MessageMetadata {
  model?: string;
  provider?: LlmProvider;
  tokens?: number;
  duration?: number;
  tools?: ToolCall[];
  reasoning?: ReasoningStep[];
}

export interface MessageReaction {
  type: '👍' | '👎' | '🔄' | '💾';
  count: number;
  userReacted?: boolean;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
  result?: any;
  status: 'pending' | 'running' | 'completed' | 'error';
  error?: string;
  duration?: number;
}

export interface ReasoningStep {
  id: string;
  type: 'thought' | 'step' | 'agent_step';
  content: string;
  agentType?: AgentType;
  timestamp: string;
  depth?: number;
}

export interface Session {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
  agentType?: AgentType;
  orchestrationMode: OrchestrationMode;
  metadata?: SessionMetadata;
}

export type OrchestrationMode = 'single_agent' | 'auto_route' | 'decomposition_thinking';

export interface SessionMetadata {
  totalMessages: number;
  totalTokens: number;
  duration: number;
  agentsInvolved: AgentType[];
  tags?: string[];
}

export interface ChatRequest {
  message: string;
  sessionId?: string;
  agentType?: AgentType;
  orchestrationMode?: OrchestrationMode;
  provider?: LlmProvider;
  model?: string;
}

export type LlmProvider =
  | 'google'
  | 'openai'
  | 'anthropic'
  | 'ollama';

export interface AppState {
  // Agent state
  agents: Agent[];
  activeAgent: AgentType | null;
  agentStatus: Record<AgentType, AgentStatus>;
  
  // Chat state
  sessions: Session[];
  currentSession: Session | null;
  messages: Message[];
  
  // UI state
  sidebarOpen: boolean;
  settingsPanelOpen: boolean;
  theme: 'dark' | 'light';
  
  // Settings
  settings: AppSettings;
}

export interface AppSettings {
  provider: LlmProvider;
  model: string;
  orchestrationMode: OrchestrationMode;
  autoSaveSessions: boolean;
  showReasoning: boolean;
  enableNotifications: boolean;
  fontSize: 'small' | 'medium' | 'large';
  language: 'en' | 'pt';
  theme?: 'dark' | 'light';
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrev: boolean;
}

// Error types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

// UI Component Props
export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
  testId?: string;
}

export interface ButtonProps extends BaseComponentProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
}

export interface InputProps extends BaseComponentProps {
  type?: string;
  value?: string;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  label?: string;
  required?: boolean;
  onChange?: (value: string) => void;
  onBlur?: () => void;
  onFocus?: () => void;
}

export interface CardProps extends BaseComponentProps {
  elevation?: 'none' | 'sm' | 'md' | 'lg';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
  clickable?: boolean;
  onClick?: () => void;
}
