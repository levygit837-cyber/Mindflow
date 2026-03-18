import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Brain, 
  CheckCircle2, 
  Circle, 
  Wrench, 
  MessageSquare, 
  AlertCircle 
} from 'lucide-react';
import type { StreamEvent } from '../hooks/useOmniStream';
import { RichText } from './common/RichText';

interface ReasoningTreeProps {
  events: StreamEvent[];
}

const ReasoningTree: React.FC<ReasoningTreeProps> = ({ events }) => {
  // Aggregate consecutive events of the same type and agent (for streaming)
  const aggregatedEvents = events.reduce((acc: StreamEvent[], event) => {
    const last = acc[acc.length - 1];
    
    // Only aggregate text-based types: response, thought, and user
    const aggregatableTypes = ['response', 'thought', 'user'];
    
    if (last && 
        last.type === event.type && 
        aggregatableTypes.includes(event.type) &&
        last.meta?.agent === event.meta?.agent) {
      
      // Merge data
      last.data += event.data;
      return acc;
    }
    
    // For other types or if first event, add as is (clone to avoid mutating originals)
    acc.push({ ...event });
    return acc;
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <AnimatePresence mode="popLayout">
        {aggregatedEvents.map((event, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            style={{ 
              display: 'flex', 
              gap: '16px',
              paddingLeft: event.type === 'thought' ? '24px' : '0'
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'var(--surface-elevated)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                color: getEventColor(event.type)
              }}>
                {getEventIcon(event.type)}
              </div>
              {index < aggregatedEvents.length - 1 && (
                <div style={{ 
                  flex: 1, 
                  width: '1px', 
                  backgroundColor: 'rgba(255, 255, 255, 0.05)', 
                  margin: '4px 0' 
                }} />
              )}
            </div>

            <div style={{ flex: 1, paddingBottom: '16px' }}>
              <div style={{ 
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '14px', 
                fontWeight: 600, 
                color: getEventColor(event.type),
                marginBottom: '4px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                {event.meta?.agent && (
                    <span style={{ 
                        backgroundColor: `var(--agent-${event.meta.agent.toLowerCase()})`,
                        color: 'var(--text-inverse)',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '11px'
                    }}>
                        {event.meta.agent}
                    </span>
                )}
                {event.type}
              </div>
              {event.type === 'response' ? (
                <RichText content={formatData(event)} className="reasoning-rich-text" />
              ) : (
                <div style={{ 
                  fontSize: '15px', 
                  color: event.type === 'thought' ? 'var(--text-secondary)' : 'var(--text-primary)',
                  fontFamily: event.type === 'thought' ? 'var(--font-mono)' : 'var(--font-sans)',
                  lineHeight: '1.6',
                  whiteSpace: 'pre-wrap'
                }}>
                  {formatData(event)}
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

const getEventIcon = (type: string) => {
  switch (type) {
    case 'user': return <MessageSquare size={16} />;
    case 'thought': return <Brain size={16} />;
    case 'step':
    case 'agent_step': return <CheckCircle2 size={16} />;
    case 'tool_call': return <Wrench size={16} />;
    case 'tool_result': return <CheckCircle2 size={16} />;
    case 'response': return <MessageSquare size={16} />;
    case 'error': return <AlertCircle size={16} />;
    default: return <Circle size={16} />;
  }
};

const getEventColor = (type: string) => {
  switch (type) {
    case 'user': return 'var(--text-primary)';
    case 'thought': return 'var(--state-thinking)';
    case 'tool_call': return 'var(--state-action)';
    case 'tool_result': return 'var(--state-success)';
    case 'response': return 'var(--brand-primary)';
    case 'error': return 'var(--state-error)';
    default: return 'var(--state-info)';
  }
};

const formatData = (event: StreamEvent) => {
  if (event.type === 'tool_call' || event.type === 'tool_result' || event.type === 'step' || event.type === 'agent_step') {
    try {
      const parsed = JSON.parse(event.data);
      if (event.type === 'tool_call') return `Calling ${parsed.name} with ${JSON.stringify(parsed.args)}`;
      if (event.type === 'tool_result') return `Result from ${parsed.name}: ${parsed.result}`;
      if (parsed.stepName) return parsed.stepName + (parsed.detail ? ` - ${parsed.detail}` : '');
    } catch (e) {}
  }
  return event.data;
};

export default ReasoningTree;
