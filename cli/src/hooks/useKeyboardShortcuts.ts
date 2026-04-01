import { useEffect } from 'react';
import { useInput } from 'ink';
import { useAppStore } from '../state/store.js';

export function useKeyboardShortcuts() {
  const { clearMessages, setExpandedView, expandedView } = useAppStore();

  useInput((input, key) => {
    // Ctrl+C is handled by Ink automatically for exit

    // Ctrl+L: Clear messages
    if (key.ctrl && input === 'l') {
      clearMessages();
    }

    // Ctrl+A: Toggle agent panel
    if (key.ctrl && input === 'a') {
      setExpandedView(expandedView === 'agents' ? 'none' : 'agents');
    }

    // Ctrl+T: Toggle tools panel
    if (key.ctrl && input === 't') {
      setExpandedView(expandedView === 'tools' ? 'none' : 'tools');
    }
  });
}
