import React from 'react';
import { motion } from 'framer-motion';
import {
  Network,
  Code,
  Search,
  Brain,
  Cpu,
  MessageSquare,
  Palette,
  Shield,
  Settings
} from 'lucide-react';

type AgentType = 'orchestrator' | 'coder' | 'analyst' | 'researcher' | 'architect' | 'critic' | 'creative' | 'security' | 'default';
type AgentStatus = 'online' | 'thinking' | 'busy' | 'offline' | 'error';
type AvatarSize = 'sm' | 'md' | 'lg';

interface AgentAvatarProps {
  agentType: AgentType;
  size?: AvatarSize;
  showStatus?: boolean;
  status?: AgentStatus;
  className?: string;
}

// Matches the design: orchestrator gets gradient, others get solid dark bg with accent icon
const AGENT_CONFIGS: Record<AgentType, { icon: React.ElementType; background: string; iconColor: string }> = {
  orchestrator: {
    icon: Network,
    background: 'linear-gradient(135deg, #7C3AFF 0%, #22D3EE 100%)',
    iconColor: '#FFFFFF',
  },
  analyst: {
    icon: Search,
    background: '#1C1208',
    iconColor: '#F59E0B',
  },
  coder: {
    icon: Code,
    background: '#071A0C',
    iconColor: '#4ADE80',
  },
  researcher: {
    icon: Brain,
    background: '#04151B',
    iconColor: '#22D3EE',
  },
  architect: {
    icon: Cpu,
    background: 'linear-gradient(135deg, #1C2340 0%, #151C30 100%)',
    iconColor: '#B0BEC5',
  },
  critic: {
    icon: MessageSquare,
    background: 'linear-gradient(135deg, #3A0A0A 0%, #2A0808 100%)',
    iconColor: '#FF7043',
  },
  creative: {
    icon: Palette,
    background: 'linear-gradient(135deg, #3A2800 0%, #2A1E00 100%)',
    iconColor: '#FFAB40',
  },
  security: {
    icon: Shield,
    background: 'linear-gradient(135deg, #3A0A0A 0%, #2A0808 100%)',
    iconColor: '#EF5350',
  },
  default: {
    icon: Settings,
    background: 'linear-gradient(135deg, #7C3AFF 0%, #22D3EE 100%)',
    iconColor: '#FFFFFF',
  },
};

const STATUS_COLORS: Record<AgentStatus, string> = {
  online: '#10B981',
  thinking: '#22D3EE',
  busy: '#F59E0B',
  offline: '#4D4575',
  error: '#EF4444',
};

const SIZE_CLASSES: Record<AvatarSize, { container: string; icon: string }> = {
  sm: { container: 'w-6 h-6', icon: 'w-3 h-3' },
  md: { container: 'w-[34px] h-[34px]', icon: 'w-[18px] h-[18px]' },
  lg: { container: 'w-12 h-12', icon: 'w-6 h-6' },
};

export const AgentAvatar: React.FC<AgentAvatarProps> = ({
  agentType,
  size = 'md',
  showStatus = false,
  status = 'online',
  className = '',
}) => {
  const config = AGENT_CONFIGS[agentType] ?? AGENT_CONFIGS.default;
  const Icon = config.icon;
  const sizes = SIZE_CLASSES[size];

  return (
    <div className={`relative inline-flex flex-shrink-0 ${className}`}>
      <motion.div
        className={`${sizes.container} rounded-lg flex items-center justify-center shadow-lg`}
        style={{ background: config.background }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        transition={{ type: 'spring', stiffness: 400, damping: 17 }}
      >
        <Icon className={sizes.icon} style={{ color: config.iconColor }} />
      </motion.div>

      {showStatus && (
        <motion.div
          className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2"
          style={{
            backgroundColor: STATUS_COLORS[status],
            borderColor: 'var(--mindflow-bg-primary)',
          }}
          animate={status === 'thinking' ? { scale: [1, 1.3, 1] } : { scale: 1 }}
          transition={{
            duration: 1.2,
            repeat: status === 'thinking' ? Infinity : 0,
            repeatType: 'reverse',
            ease: 'easeInOut',
          }}
        />
      )}
    </div>
  );
};

export default AgentAvatar;
