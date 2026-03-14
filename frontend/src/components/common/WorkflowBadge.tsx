import React from 'react';
import { motion } from 'framer-motion';
import { GitBranch, Zap, Users, ArrowRight } from 'lucide-react';

interface WorkflowBadgeProps {
  type: 'parallel' | 'sequential' | 'orchestrator' | 'chain';
  label?: string;
  showIcon?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

export const WorkflowBadge: React.FC<WorkflowBadgeProps> = ({
  type,
  label,
  showIcon = true,
  size = 'md',
  className = ''
}) => {
  const getWorkflowConfig = (type: string) => {
    switch (type) {
      case 'parallel':
        return {
          icon: Zap,
          bgColor: 'var(--mindflow-bg-workflow)',
          borderColor: 'var(--mindflow-border-workflow)',
          color: 'var(--state-thinking)',
          defaultLabel: 'Parallel'
        };
      case 'sequential':
        return {
          icon: ArrowRight,
          bgColor: 'var(--mindflow-bg-workflow)',
          borderColor: 'var(--mindflow-border-workflow)',
          color: 'var(--state-thinking)',
          defaultLabel: 'Sequential'
        };
      case 'orchestrator':
        return {
          icon: Users,
          bgColor: 'var(--mindflow-bg-workflow)',
          borderColor: 'var(--mindflow-border-workflow)',
          color: 'var(--state-thinking)',
          defaultLabel: 'Orchestrator'
        };
      case 'chain':
        return {
          icon: GitBranch,
          bgColor: 'var(--mindflow-bg-workflow)',
          borderColor: 'var(--mindflow-border-workflow)',
          color: 'var(--state-thinking)',
          defaultLabel: 'Chain'
        };
      default:
        return {
          icon: GitBranch,
          bgColor: 'var(--mindflow-bg-workflow)',
          borderColor: 'var(--mindflow-border-workflow)',
          color: 'var(--state-thinking)',
          defaultLabel: 'Unknown'
        };
    }
  };

  const getSizeClasses = (size: string) => {
    switch (size) {
      case 'sm':
        return 'py-1 px-2 gap-1 text-xs';
      default:
        return 'py-1.5 px-2.5 gap-1.5 text-xs';
    }
  };

  const getIconSize = (size: string) => {
    switch (size) {
      case 'sm':
        return 'w-3 h-3';
      default:
        return 'w-3 h-3';
    }
  };

  const config = getWorkflowConfig(type);
  const Icon = config.icon;
  const sizeClasses = getSizeClasses(size);
  const iconSize = getIconSize(size);

  return (
    <motion.div
      className={`
        inline-flex items-center rounded-md
        border
        ${sizeClasses}
        ${className}
      `}
      style={{
        backgroundColor: config.bgColor,
        borderColor: config.borderColor,
        color: config.color
      }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      transition={{ duration: 0.2 }}
    >
      {showIcon && (
        <Icon className={iconSize} />
      )}
      
      <span 
        className="font-medium"
        style={{ fontFamily: 'var(--font-brand)' }}
      >
        {label || config.defaultLabel}
      </span>
    </motion.div>
  );
};

export default WorkflowBadge;
