// TODO: Extract all inline style objects to CSS modules or Tailwind classes.
// Current inline styles make it hard to maintain consistent theming and
// prevent static analysis of design-token usage. Target: zero inline style
// props on structural elements; keep only dynamic values (e.g. agent colors).
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Terminal,
  BarChart3,
  Search,
  Layers,
  ShieldCheck,
  Settings,
  Cpu,
  Send,
  Plus,
  MessageSquare,
  Clock,
  Lightbulb,
  Shield
} from 'lucide-react';
import { useOmniStream } from '../hooks/useOmniStream';
import type { StreamEvent } from '../hooks/useOmniStream';
import { useChatSessions } from '../hooks/useChatSessions';
import { useAppStore } from '../stores/appStore';
import ReasoningTree from './ReasoningTree';

const AGENTS = [
  { id: 'coder', name: 'Coder', icon: Terminal, color: 'var(--agent-coder)' },
  { id: 'analyst', name: 'Analyst', icon: BarChart3, color: 'var(--agent-analyst)' },
  { id: 'researcher', name: 'Researcher', icon: Search, color: 'var(--agent-researcher)' },
  { id: 'arch_tech', name: 'ArchTech', icon: Layers, color: 'var(--agent-arch-tech)' },
  { id: 'critic', name: 'Critic', icon: ShieldCheck, color: 'var(--agent-critic)' },
  { id: 'creative', name: 'Creative', icon: Lightbulb, color: 'var(--agent-creative)' },
  { id: 'security_guard', name: 'SecurityGuard', icon: Shield, color: 'var(--agent-security-guard)' },
];

const BASE_URL = 'http://localhost:8000';

const AgentDashboard: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const { setActiveAgent: setActiveAgentStore, activeAgent } = useAppStore();
  
  const { 
    sessions, 
    currentSessionId, 
    setCurrentSessionId, 
    fetchSessions,
    getSessionHistory 
  } = useChatSessions(BASE_URL);

  const { 
    events, 
    isStreaming, 
    startStream,
    clearEvents,
    setInitialEvents 
  } = useOmniStream(`${BASE_URL}/v1/agent/chat/stream`);

  // Auto-detect agent from stream events
  useEffect(() => {
    const lastEventWithAgent = [...events].reverse().find(e => e.meta?.agent);
    if (lastEventWithAgent && lastEventWithAgent.meta?.agent) {
      setActiveAgentStore(lastEventWithAgent.meta.agent.toLowerCase());
    }
  }, [events]);

  // Load session history when currentSessionId changes
  useEffect(() => {
    if (currentSessionId) {
      getSessionHistory(currentSessionId).then(session => {
        if (session && session.messages) {
          // Convert database messages to stream events for the UI
          const historyEvents: StreamEvent[] = session.messages.map(msg => ({
            type: msg.role === 'user' ? 'user' : 'response', // Simplify for UI
            data: msg.content,
            meta: { 
                agent: msg.role === 'user' ? 'USER' : (msg.model || 'ASSISTANT'),
                timestamp: msg.created_at
            }
          }));
          setInitialEvents(historyEvents);
        }
      });
    } else {
      clearEvents();
    }
  }, [currentSessionId, getSessionHistory, setInitialEvents, clearEvents]);

  const handleNewSession = () => {
    setCurrentSessionId(null);
    clearEvents();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isStreaming) return;
    
    const sessionId = currentSessionId || `sess-${crypto.randomUUID()}`;
    if (!currentSessionId) {
        setCurrentSessionId(sessionId);
    }

    // Add user message to UI immediately as a "user" event
    const userEvent: StreamEvent = {
        type: 'user',
        data: inputValue,
        meta: { agent: 'USER' }
    };
    setInitialEvents([...events, userEvent]);

    startStream({
      message: inputValue,
      session_id: sessionId,
      agent: (activeAgent || 'coder').toUpperCase(),
      orchestrate: true
    }).then(() => {
        fetchSessions(); // Refresh list to update titles/timestamps
    });
    
    setInputValue('');
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: 'var(--background)' }}>
      {/* Sessions Sidebar */}
      <aside className="glass-surface" style={{ 
        width: '260px', 
        display: 'flex', 
        flexDirection: 'column', 
        borderRight: '1px solid rgba(255, 255, 255, 0.05)',
        zIndex: 10
      }}>
        <div style={{ padding: '20px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <button 
                onClick={handleNewSession}
                className="glass-surface"
                style={{
                    width: '100%',
                    padding: '10px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontWeight: 500,
                    border: '1px solid rgba(255, 255, 255, 0.1)'
                }}
            >
                <Plus size={18} /> New Chat
            </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-disabled)', marginBottom: '12px', paddingLeft: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Recent History
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {sessions.map(s => (
                    <button
                        key={s.id}
                        onClick={() => setCurrentSessionId(s.id)}
                        style={{
                            width: '100%',
                            padding: '10px 12px',
                            borderRadius: '8px',
                            textAlign: 'left',
                            background: currentSessionId === s.id ? 'rgba(255, 255, 255, 0.05)' : 'none',
                            border: 'none',
                            color: currentSessionId === s.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            transition: 'all 0.2s'
                        }}
                    >
                        <MessageSquare size={16} color={currentSessionId === s.id ? 'var(--brand-primary)' : 'var(--text-disabled)'} />
                        <div style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '13px' }}>
                            {s.title}
                        </div>
                    </button>
                ))}
            </div>
        </div>

        <div style={{ padding: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '8px' }}>
                <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--surface-elevated)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Settings size={16} color="var(--text-secondary)" />
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Settings</div>
            </div>
        </div>
      </aside>

      {/* Agents Mini-Sidebar */}
      <aside className="glass-surface" style={{ 
        width: '68px', 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        padding: '24px 0',
        borderRight: '1px solid rgba(255, 255, 255, 0.05)',
        zIndex: 10
      }}>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '20px', flex: 1 }}>
          {AGENTS.map((agent) => (
            <button
              key={agent.id}
              onClick={() => setActiveAgentStore(agent.id as any)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '10px',
                borderRadius: '12px',
                color: activeAgent === agent.id ? agent.color : 'var(--text-disabled)',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative'
              }}
              title={agent.name}
            >
              <agent.icon size={22} />
              {activeAgent === agent.id && (
                <motion.div
                  layoutId="active-indicator"
                  style={{
                    position: 'absolute',
                    left: '-4px',
                    width: '4px',
                    height: '24px',
                    background: agent.color,
                    borderRadius: '0 4px 4px 0'
                  }}
                />
              )}
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Viewport */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
        {/* Header */}
        <header style={{ 
          height: '64px', 
          padding: '0 32px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          backgroundColor: 'rgba(10, 10, 11, 0.8)',
          backdropFilter: 'blur(8px)',
          zIndex: 5
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' }}>MindFlow</span>
            <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>/</span>
            <span style={{ 
              fontSize: '14px', 
              fontWeight: 500, 
              color: AGENTS.find(a => a.id === activeAgent)?.color 
            }}>
              {AGENTS.find(a => a.id === activeAgent)?.name}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={14} color="var(--text-disabled)" />
                <span style={{ fontSize: '12px', color: 'var(--text-disabled)' }}>
                    Session: {currentSessionId ? currentSessionId.slice(-8) : 'New'}
                </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ 
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                background: isStreaming ? 'var(--state-thinking)' : 'var(--state-success)',
                boxShadow: isStreaming ? '0 0 12px var(--state-thinking)' : '0 0 12px var(--state-success)',
                animation: isStreaming ? 'pulse 2s infinite' : 'none'
                }} />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>
                    {isStreaming ? 'Agent Thinking...' : 'System Ready'}
                </span>
            </div>
          </div>
        </header>

        {/* Content (Timeline) */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '32px', scrollBehavior: 'smooth' }}>
          <div style={{ maxWidth: '900px', margin: '0 auto' }}>
            {events.length === 0 ? (
                <div className="glass-surface" style={{ padding: '64px', borderRadius: '24px', border: '1px dashed rgba(255, 255, 255, 0.1)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', marginTop: '40px' }}>
                    <div style={{ padding: '20px', borderRadius: '20px', background: 'rgba(255, 255, 255, 0.02)' }}>
                        <Cpu size={48} color="var(--brand-primary)" style={{ opacity: 0.8 }} />
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <h2 style={{ color: 'var(--text-primary)', fontSize: '20px', marginBottom: '8px' }}>Welcome to MindFlow</h2>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', maxWidth: '400px', lineHeight: '1.5' }}>
                            I'm your engineering assistant. Select an agent personality or ask a complex question to trigger multi-step reasoning.
                        </p>
                    </div>
                </div>
            ) : (
                <ReasoningTree events={events} />
            )}
          </div>
        </div>

        {/* Input Area */}
        <div style={{ padding: '24px 32px 32px', backgroundColor: 'transparent', zIndex: 10 }}>
          <form onSubmit={handleSubmit} style={{ maxWidth: '900px', margin: '0 auto', position: 'relative' }}>
            <div className="glass-surface" style={{ 
              padding: '16px 20px', 
              borderRadius: '20px', 
              display: 'flex', 
              alignItems: 'center',
              gap: '16px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              boxShadow: '0 12px 48px rgba(0, 0, 0, 0.5)'
            }}>
              <input 
                type="text" 
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={isStreaming}
                placeholder="Ask MindFlow anything..." 
                style={{
                  background: 'none',
                  border: 'none',
                  flex: 1,
                  color: 'var(--text-primary)',
                  fontSize: '16px',
                  outline: 'none'
                }}
              />
              <button 
                type="submit"
                disabled={isStreaming || !inputValue.trim()}
                style={{
                    background: isStreaming ? 'var(--brand-secondary)' : 'var(--brand-primary)',
                    border: 'none',
                    borderRadius: '10px',
                    width: '40px',
                    height: '40px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    cursor: isStreaming ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                    boxShadow: isStreaming ? 'none' : '0 4px 12px rgba(var(--brand-primary-rgb), 0.3)'
                }}
              >
                <Send size={20} />
              </button>
            </div>
          </form>
        </div>
      </main>

    </div>
  );
};

export default AgentDashboard;
