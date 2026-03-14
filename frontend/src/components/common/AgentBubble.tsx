import React from 'react';
import { motion } from 'framer-motion';
import { Network, Search, Code2, BarChart2 } from 'lucide-react';
import { format } from 'date-fns';

type AgentType = 'orchestrator' | 'coder' | 'analyst' | 'researcher' | 'architect' | 'critic' | 'creative' | 'security' | 'default';

interface AgentBubbleProps {
  agentType: AgentType;
  agentName: string;
  content: string;
  timestamp: Date;
  model?: string;
  className?: string;
}

const CONFIGS: Record<string, {
  nameColor: string;
  avatarBg: string | 'gradient';
  avatarBorder: string;
  Icon: React.FC<{ size: number; color: string }>;
  iconColor: string;
  badgeBg: string;
  badgeText: string;
  bubbleBg: string;
  bubbleBorder: string;
  textColor: string;
}> = {
  orchestrator: {
    nameColor: '#A78BFA',
    avatarBg: 'gradient',
    avatarBorder: 'none',
    Icon: ({ size, color }) => <Network size={size} color={color} />,
    iconColor: '#FFFFFF',
    badgeBg: '#1D1840',
    badgeText: '#4D4575',
    bubbleBg: '#130F28',
    bubbleBorder: '#1A1545',
    textColor: '#C4BEED',
  },
  analyst: {
    nameColor: '#F59E0B',
    avatarBg: '#1C1208',
    avatarBorder: '#F59E0B',
    Icon: ({ size, color }) => <BarChart2 size={size} color={color} />,
    iconColor: '#F59E0B',
    badgeBg: '#2A1800',
    badgeText: '#F59E0B',
    bubbleBg: '#1C1208',
    bubbleBorder: '#3D2800',
    textColor: '#C9A86A',
  },
  coder: {
    nameColor: '#4ADE80',
    avatarBg: '#071A0C',
    avatarBorder: '#4ADE80',
    Icon: ({ size, color }) => <Code2 size={size} color={color} />,
    iconColor: '#4ADE80',
    badgeBg: '#071A0C',
    badgeText: '#4ADE80',
    bubbleBg: '#071A0C',
    bubbleBorder: '#0D3018',
    textColor: '#8ECF9E',
  },
  researcher: {
    nameColor: '#22D3EE',
    avatarBg: '#0A1520',
    avatarBorder: '#22D3EE',
    Icon: ({ size, color }) => <Search size={size} color={color} />,
    iconColor: '#22D3EE',
    badgeBg: '#0A1520',
    badgeText: '#22D3EE',
    bubbleBg: '#0A1520',
    bubbleBorder: '#0F2A3F',
    textColor: '#A8D4E6',
  },
  default: {
    nameColor: '#A78BFA',
    avatarBg: 'gradient',
    avatarBorder: 'none',
    Icon: ({ size, color }) => <Network size={size} color={color} />,
    iconColor: '#FFFFFF',
    badgeBg: '#1D1840',
    badgeText: '#4D4575',
    bubbleBg: '#130F28',
    bubbleBorder: '#1A1545',
    textColor: '#C4BEED',
  },
};

export const AgentBubble: React.FC<AgentBubbleProps> = ({
  agentType,
  agentName,
  content,
  timestamp,
  model,
  className = '',
}) => {
  const cfg = CONFIGS[agentType] ?? CONFIGS.default;
  const { Icon } = cfg;
  const isGradient = cfg.avatarBg === 'gradient';

  return (
    <motion.div
      className={`flex w-full ${className}`}
      style={{ gap: 14 }}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
    >
      {/* Avatar */}
      <div
        className="flex items-center justify-center flex-shrink-0"
        style={{
          width: 36,
          height: 36,
          borderRadius: isGradient ? 10 : 8,
          background: isGradient
            ? 'linear-gradient(135deg, #7C3AFF 0%, #22D3EE 100%)'
            : (cfg.avatarBg as string),
          border: cfg.avatarBorder !== 'none' ? `1px solid ${cfg.avatarBorder}` : undefined,
        }}
      >
        <Icon size={16} color={cfg.iconColor} />
      </div>

      {/* Body */}
      <div className="flex-1 min-w-0" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* Header */}
        <div className="flex items-center" style={{ gap: 8 }}>
          <span
            style={{
              color: cfg.nameColor,
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {agentName}
          </span>

          {model && (
            <div
              style={{
                backgroundColor: cfg.badgeBg,
                borderRadius: 4,
                padding: '2px 8px',
              }}
            >
              <span
                style={{
                  color: cfg.badgeText,
                  fontFamily: 'Space Grotesk, sans-serif',
                  fontSize: 10,
                  fontWeight: 500,
                }}
              >
                {model}
              </span>
            </div>
          )}

          <span
            style={{
              color: '#4D4575',
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
            }}
          >
            {format(timestamp, 'HH:mm')}
          </span>
        </div>

        {/* Bubble */}
        <div
          style={{
            backgroundColor: cfg.bubbleBg,
            border: `1px solid ${cfg.bubbleBorder}`,
            borderRadius: '4px 14px 14px 14px',
            padding: '16px 20px',
          }}
        >
          <p
            style={{
              color: cfg.textColor,
              fontFamily: 'Inter, sans-serif',
              fontSize: 14,
              lineHeight: 1.65,
              margin: 0,
              whiteSpace: 'pre-wrap',
            }}
          >
            {content}
          </p>
        </div>
      </div>
    </motion.div>
  );
};

export default AgentBubble;
