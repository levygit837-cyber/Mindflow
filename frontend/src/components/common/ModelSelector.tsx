import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, ChevronDown } from 'lucide-react';

interface ModelSelectorProps {
  selectedModel: string;
  models: string[];
  onModelChange: (model: string) => void;
  size?: 'sm' | 'md';
  className?: string;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  models,
  onModelChange,
  size = 'md',
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const getSizeClasses = (size: string) => {
    switch (size) {
      case 'sm':
        return 'py-1.5 px-2 gap-1.5 text-xs';
      default:
        return 'py-2 px-3 gap-2 text-xs';
    }
  };

  const getIconSize = (size: string) => {
    switch (size) {
      case 'sm':
        return 'w-3 h-3';
      default:
        return 'w-3.5 h-3.5';
    }
  };

  const sizeClasses = getSizeClasses(size);
  const iconSize = getIconSize(size);

  const handleModelSelect = (model: string) => {
    onModelChange(model);
    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`}>
      {/* Button */}
      <motion.button
        className={`
          inline-flex items-center rounded-lg
          bg-[var(--mindflow-bg-model)]
          border border-[var(--mindflow-border-model)]
          text-[var(--text-accent)]
          ${sizeClasses}
        `}
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        transition={{ duration: 0.2 }}
      >
        <Cpu className={iconSize} />
        <span 
          className="font-medium"
          style={{ fontFamily: 'var(--font-brand)' }}
        >
          {selectedModel}
        </span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-3 h-3 text-[var(--text-meta)]" />
        </motion.div>
      </motion.button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="
              absolute top-full mt-1 right-0 z-50
              bg-[var(--mindflow-bg-card)]
              border border-[var(--mindflow-border)]
              rounded-lg shadow-lg
              min-w-[200px]
              overflow-hidden
            "
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <div className="py-1">
              {models.map((model) => (
                <motion.button
                  key={model}
                  className={`
                    w-full px-3 py-2 text-left text-xs
                    hover:bg-[var(--mindflow-bg-active-session)]
                    transition-colors duration-150
                    ${model === selectedModel ? 'text-[var(--text-accent)] font-medium' : 'text-[var(--text-secondary)]'}
                  `}
                  onClick={() => handleModelSelect(model)}
                  whileHover={{ x: 2 }}
                  transition={{ duration: 0.1 }}
                >
                  <div className="flex items-center gap-2">
                    <Cpu className="w-3 h-3" />
                    <span style={{ fontFamily: 'var(--font-brand)' }}>
                      {model}
                    </span>
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};

export default ModelSelector;
