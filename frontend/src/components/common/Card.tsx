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
  const baseClasses = ['panel-surface'];

  const elevationClasses = {
    none: [],
    sm: ['shadow-sm'],
    md: ['shadow-md'],
    lg: ['shadow-lg'],
  } as const;

  const paddingClasses = {
    none: [],
    sm: ['p-3'],
    md: ['p-4'],
    lg: ['p-6'],
  } as const;

  const interactiveClasses = hover || clickable ? ['panel-hover'] : [];
  const clickableClasses = clickable ? ['cursor-pointer'] : [];

  const classes = [
    ...baseClasses,
    ...elevationClasses[elevation],
    ...paddingClasses[padding],
    ...interactiveClasses,
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
        whileHover: hover ? { y: -2 } : undefined,
        whileTap: clickable ? { y: 1 } : undefined,
        transition: { duration: 0.18 },
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
