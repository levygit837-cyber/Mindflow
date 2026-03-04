import React from 'react';
import { motion } from 'framer-motion';
import type { ButtonProps } from '../../types';

const Button: React.FC<ButtonProps> = ({
  children,
  className = '',
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  icon,
  onClick,
  type = 'button',
  testId,
}) => {
  const baseClasses = [
    'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed',
  ];

  const variantClasses = {
    primary: [
      'bg-gradient-to-r from-brand-primary to-brand-primary-light text-white hover:from-brand-primary-dark hover:to-brand-primary focus:ring-brand-primary shadow-lg hover:shadow-xl',
    ],
    secondary: [
      'bg-surface-elevated text-text-primary border border-border hover:bg-surface focus:ring-brand-primary',
    ],
    ghost: [
      'text-text-secondary hover:text-text-primary hover:bg-surface-elevated focus:ring-brand-primary',
    ],
    danger: [
      'bg-state-error text-white hover:bg-red-600 focus:ring-state-error',
    ],
  };

  const sizeClasses = {
    sm: ['px-3 py-1.5 text-sm'],
    md: ['px-4 py-2 text-base'],
    lg: ['px-6 py-3 text-lg'],
  };

  const classes = [
    ...baseClasses,
    ...variantClasses[variant],
    ...sizeClasses[size],
    className,
  ].join(' ');

  const handleClick = () => {
    if (!disabled && !loading && onClick) {
      onClick();
    }
  };

  return (
    <motion.button
      type={type}
      className={classes}
      onClick={handleClick}
      disabled={disabled || loading}
      data-testid={testId}
      whileHover={{ scale: disabled || loading ? 1 : 1.02 }}
      whileTap={{ scale: disabled || loading ? 1 : 0.98 }}
      transition={{ duration: 0.15 }}
    >
      {loading && (
        <svg
          className="animate-spin -ml-1 mr-2 h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      
      {icon && !loading && (
        <span className="mr-2">{icon}</span>
      )}
      
      {children}
    </motion.button>
  );
};

export default Button;
