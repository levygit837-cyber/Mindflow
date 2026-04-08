import React from 'react';
import { cn } from '../../lib/utils';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  accentColor?: string;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, accentColor, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'bg-[#1a1a1a] rounded-xl border border-[#2a2a2a] overflow-hidden',
          accentColor && 'border-l-[3px]',
          className
        )}
        style={accentColor ? { borderLeftColor: accentColor } : undefined}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center justify-between p-3 border-b border-[#2a2a2a]', className)} {...props} />
  )
);
CardHeader.displayName = 'CardHeader';

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-3', className)} {...props} />
  )
);
CardContent.displayName = 'CardContent';

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center p-3 border-t border-[#2a2a2a]', className)} {...props} />
  )
);
CardFooter.displayName = 'CardFooter';

export default Card;
