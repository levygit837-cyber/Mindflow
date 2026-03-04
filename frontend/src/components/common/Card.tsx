import React from 'react';
import { motion } from 'framer-motion';
import type { CardProps } from '../../types';

const Card: React.FC<CardProps> = ({
  children,
  className = '',
  elevation = 'md',
  padding = 'md',
  hover = false,
  clickable = false,
  onClick,
  testId,
}) => {
  const baseClasses = [
    'bg-surface rounded-lg transition-all duration-200',
  ];

  const elevationClasses = {
    none: [],
    sm: ['shadow-sm'],
    md: ['shadow-md'],
    lg: ['shadow-lg'],
  };

  const paddingClasses = {
    none: [],
    sm: ['p-3'],
    md: ['p-4'],
    lg: ['p-6'],
  };

  const hoverClasses = hover
    ? [
        'hover:shadow-lg hover:scale-[1.02] cursor-pointer',
        clickable ? 'cursor-pointer' : '',
      ]
    : [];

  const clickableClasses = clickable
    ? ['cursor-pointer active:scale-[0.98]']
    : [];

  const classes = [
    ...baseClasses,
    ...elevationClasses[elevation],
    ...paddingClasses[padding],
    ...hoverClasses,
    ...clickableClasses,
    className,
  ].join(' ');

  const handleClick = () => {
    if (clickable && onClick) {
      onClick();
    }
  };

  const MotionComponent = clickable || hover ? motion.div : 'div';
  const motionProps = clickable || hover
    ? {
        whileHover: hover ? { scale: 1.02 } : undefined,
        whileTap: clickable ? { scale: 0.98 } : undefined,
        transition: { duration: 0.15 },
        onClick: handleClick,
      }
    : {};

  return (
    <MotionComponent
      className={classes}
      data-testid={testId}
      {...motionProps}
    >
      {children}
    </MotionComponent>
  );
};

export default Card;
