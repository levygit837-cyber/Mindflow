import React, { forwardRef } from 'react';
import { motion } from 'framer-motion';
import type { InputProps } from '../../types';

const Input = forwardRef<HTMLInputElement, InputProps>(({
  className = '',
  type = 'text',
  value,
  placeholder,
  disabled = false,
  error,
  label,
  required = false,
  onChange,
  onBlur,
  onFocus,
  testId,
}, ref) => {
  const baseClasses = [
    'w-full px-3 py-2 bg-surface border border-border rounded-lg text-text-primary placeholder-text-disabled transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed',
  ];

  const errorClasses = error
    ? ['border-state-error focus:ring-state-error']
    : [];

  const classes = [
    ...baseClasses,
    ...errorClasses,
    className,
  ].join(' ');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (onChange) {
      onChange(e.target.value);
    }
  };

  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-text-primary mb-1">
          {label}
          {required && <span className="text-state-error ml-1">*</span>}
        </label>
      )}
      
      <motion.input
        ref={ref}
        type={type}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        className={classes}
        onChange={handleChange}
        onBlur={onBlur}
        onFocus={onFocus}
        data-testid={testId}
        whileFocus={{ scale: 1.01 }}
        transition={{ duration: 0.15 }}
      />
      
      {error && (
        <motion.p
          className="mt-1 text-sm text-state-error"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {error}
        </motion.p>
      )}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;
