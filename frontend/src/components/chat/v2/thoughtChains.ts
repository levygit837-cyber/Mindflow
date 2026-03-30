// Thought Chains - Grouping and Filtering Logic
// FEATURE: chat-visualization-v2

import type { MindflowV2AgentType } from './types';

export interface ThoughtChainItem {
  id: string;
  agentType: MindflowV2AgentType;
  title?: string;
  status?: string;
  content: string;
  summary?: string;
  defaultExpanded?: boolean;
}

export interface ThoughtChain {
  id: string;
  agentType: MindflowV2AgentType;
  items: ThoughtChainItem[];
  title?: string;
}

export function filterThoughtContent(content: string): string {
  let filtered = content;

  filtered = filtered.replace(/\b(delegated|delegation)\b/gi, '');
  filtered = filtered.replace(/\b(reasoning\s+)?depth\s*:\s*\d+/gi, '');
  filtered = filtered.replace(/\b(thought\s+)?summary\s*:/gi, '');
  filtered = filtered.replace(/\s+/g, ' ').trim();

  return filtered;
}

export function filterThoughtItem(item: ThoughtChainItem): ThoughtChainItem {
  return {
    ...item,
    content: filterThoughtContent(item.content),
    summary: undefined,
  };
}

function areThoughtsRelated(
  prev: ThoughtChainItem,
  current: ThoughtChainItem,
  index: number,
  prevIndex: number
): boolean {
  if (prev.agentType !== current.agentType) {
    return false;
  }

  if (index - prevIndex > 2) {
    return false;
  }

  if (prev.status?.toLowerCase().includes('decision') || current.status?.toLowerCase().includes('decision')) {
    return false;
  }

  if (prev.content.length < 50) {
    return true;
  }

  const continuationMarkers = [
    /^(and|also|additionally|furthermore|moreover|next|then|after)/i,
    /^\d+\./,
    /^[-•*]/,
  ];

  if (continuationMarkers.some(pattern => pattern.test(current.content.trim()))) {
    return true;
  }

  return true;
}

export function groupThoughtsIntoChains(thoughts: ThoughtChainItem[]): ThoughtChain[] {
  if (thoughts.length === 0) {
    return [];
  }

  const chains: ThoughtChain[] = [];
  let currentChain: ThoughtChain | null = null;

  thoughts.forEach((thought, index) => {
    const filteredThought = filterThoughtItem(thought);

    if (currentChain && currentChain.items.length > 0) {
      const lastItem = currentChain.items[currentChain.items.length - 1];
      const lastIndex = thoughts.findIndex(t => t.id === lastItem.id);

      if (areThoughtsRelated(lastItem, thought, index, lastIndex)) {
        currentChain.items.push(filteredThought);
        return;
      }
    }

    if (currentChain && currentChain.items.length > 0) {
      chains.push(currentChain);
    }

    currentChain = {
      id: `chain-${chains.length}`,
      agentType: thought.agentType,
      items: [filteredThought],
      title: thought.title,
    };
  });

  if (currentChain && currentChain.items.length > 0) {
    chains.push(currentChain);
  }

  return chains;
}

export function shouldRenderAsChain(chain: ThoughtChain): boolean {
  return chain.items.length > 1;
}
