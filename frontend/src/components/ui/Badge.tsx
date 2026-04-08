import React from 'react';
import { cn } from '../../lib/utils';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'outline' | 'agent';
  agentColor?: string;
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', agentColor, children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center rounded px-2 py-0.5 text-xs font-medium uppercase tracking-wider';
    
    const variants = {
      default: 'bg-[#2a2a2a] text-[#b0b0b0] border border-[#2a2a2a]',
      outline: 'bg-transparent text-[#b0b0b0] border border-[#3a3a3a]',
      agent: '',
    };

    const agentStyle = variant === 'agent' && agentColor
      ? { 
          backgroundColor: `${agentColor}15`,
          borderColor: `${agentColor}40`,
          color: agentColor,
          border: '1px solid'
        }
      : undefined;

    return (
      <span
        ref={ref}
        className={cn(baseStyles, variant === 'agent' ? '' : variants[variant], className)}
        style={agentStyle}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export default Badge;
