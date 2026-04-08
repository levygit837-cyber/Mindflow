import React from 'react';
import { cn } from '../../lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'agent';
  size?: 'sm' | 'md' | 'lg';
  agentColor?: string;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', agentColor, children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center rounded-lg font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0D6E6E] disabled:opacity-50 disabled:pointer-events-none';
    
    const variants = {
      primary: 'bg-[#0D6E6E] text-white hover:bg-[#0a5a5a]',
      secondary: 'bg-[#3a3a3a] text-white hover:bg-[#4a4a4a] border border-[#3a3a3a]',
      ghost: 'bg-transparent text-white hover:bg-white/10 border border-[#2a2a2a]',
      agent: agentColor ? '' : 'bg-[#0D6E6E] text-white',
    };

    const sizes = {
      sm: 'px-3 py-1.5 text-xs',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
    };

    const agentStyle = variant === 'agent' && agentColor
      ? { backgroundColor: agentColor, color: 'white' }
      : undefined;

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        style={agentStyle}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
