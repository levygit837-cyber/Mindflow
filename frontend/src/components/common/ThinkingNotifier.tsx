import React from 'react';
import { motion } from 'framer-motion';
import {
  Network, Zap, Search, Code2, BarChart2,
} from 'lucide-react';

type AgentType = 'orchestrator' | 'coder' | 'analyst' | 'researcher' | 'default';

interface ThinkingNotifierProps {
  agentType?: AgentType;
  agentName?: string;
  status?: 'thinking' | 'processing' | 'analyzing' | 'waiting';
  className?: string;
}

const CONFIGS: Record<string, {
  avatarBg: string;
  avatarBorder: string;
  Icon: React.FC<{ size: number; color: string }>;
  accentColor: string;
  bubbleBg: string;
  bubbleBorder: string;
  label: string;
}> = {
  orchestrator: {
    avatarBg: '#1C1208',
    avatarBorder: '#F59E0B',
    Icon: ({ size, color }) => <Zap size={size} color={color} fill={color} />,
    accentColor: '#F59E0B',
    bubbleBg: '#120D04',
    bubbleBorder: '#2D1F00',
    label: 'está pensando',
  },
  analyst: {
    avatarBg: '#1C1208',
    avatarBorder: '#F59E0B',
    Icon: ({ size, color }) => <BarChart2 size={size} color={color} />,
    accentColor: '#F59E0B',
    bubbleBg: '#120D04',
    bubbleBorder: '#2D1F00',
    label: 'analisando',
  },
  coder: {
    avatarBg: '#071A0C',
    avatarBorder: '#4ADE80',
    Icon: ({ size, color }) => <Code2 size={size} color={color} />,
    accentColor: '#4ADE80',
    bubbleBg: '#041208',
    bubbleBorder: '#0D3018',
    label: 'escrevendo código',
  },
  researcher: {
    avatarBg: '#04151B',
    avatarBorder: '#22D3EE',
    Icon: ({ size, color }) => <Search size={size} color={color} />,
    accentColor: '#22D3EE',
    bubbleBg: '#031118',
    bubbleBorder: '#0A2F3A',
    label: 'pesquisando',
  },
  default: {
    avatarBg: '#110A2E',
    avatarBorder: '#7C3AFF',
    Icon: ({ size, color }) => <Network size={size} color={color} />,
    accentColor: '#A78BFA',
    bubbleBg: '#110A2E',
    bubbleBorder: '#2A1F5A',
    label: 'processando',
  },
};

export const ThinkingNotifier: React.FC<ThinkingNotifierProps> = ({
  agentType = 'orchestrator',
  agentName,
  className = '',
}) => {
  const cfg = CONFIGS[agentType] ?? CONFIGS.default;
  const displayName = agentName ?? (agentType.charAt(0).toUpperCase() + agentType.slice(1));
  const { Icon } = cfg;

  return (
    <motion.div
      className={`flex items-center ${className}`}
      style={{ gap: 14 }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
    >
      {/* Avatar */}
      <div
        className="flex items-center justify-center flex-shrink-0"
        style={{
          width: 34,
          height: 34,
          borderRadius: 10,
          backgroundColor: cfg.avatarBg,
          border: `1px solid ${cfg.avatarBorder}`,
        }}
      >
        <Icon size={15} color={cfg.accentColor} />
      </div>

      {/* Thinking bubble */}
      <div
        className="flex items-center"
        style={{
          backgroundColor: cfg.bubbleBg,
          border: `1px solid ${cfg.bubbleBorder}`,
          borderRadius: '4px 14px 14px 14px',
          padding: '10px 16px',
          gap: 10,
        }}
      >
        <span
          style={{
            color: cfg.accentColor,
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          {displayName} {cfg.label}
        </span>

        {/* 3 animated dots */}
        <div className="flex items-center" style={{ gap: 5 }}>
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              style={{
                display: 'inline-block',
                width: 5,
                height: 5,
                borderRadius: '50%',
                backgroundColor: cfg.accentColor,
              }}
              animate={{ opacity: [1, 0.25, 1] }}
              transition={{
                duration: 1.4,
                repeat: Infinity,
                repeatType: 'loop',
                ease: 'easeInOut',
                delay: i * 0.22,
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
};

export default ThinkingNotifier;
