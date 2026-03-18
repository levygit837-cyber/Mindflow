/**
 * Thought Chains - Grouping and Filtering Logic
 *
 * Implements logic to group related thoughts into chains and filter
 * out specific indicators per requirements 11.1-11.5.
 */

import { MindflowV2AgentType } from './types';

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

/**
 * Filter content to remove specific indicators per requirements 11.3-11.5:
 * - "Delegated" indicators
 * - Reasoning depth indicators
 * - Thought Summary
 */
export function filterThoughtContent(content: string): string {
  let filtered = content;

  // Remove "Delegated" indicators (case-insensitive)
  filtered = filtered.replace(/\b(delegated|delegation)\b/gi, '');

  // Remove reasoning depth indicators (e.g., "Depth: 1", "Reasoning depth: 2")
  filtered = filtered.replace(/\b(reasoning\s+)?depth\s*:\s*\d+/gi, '');

  // Remove thought summary markers
  filtered = filtered.replace(/\b(thought\s+)?summary\s*:/gi, '');

  // Clean up extra whitespace
  filtered = filtered.replace(/\s+/g, ' ').trim();

  return filtered;
}

/**
 * Filter thought item to remove summary field and filter content
 */
export function filterThoughtItem(item: ThoughtChainItem): ThoughtChainItem {
  return {
    ...item,
    content: filterThoughtContent(item.content),
    summary: undefined, // Remove summary per requirement 11.5
  };
}

/**
 * Determine if two thoughts are related and should be grouped together.
 *
 * Thoughts are related if:
 * - They are from the same agent
 * - They are consecutive in the stream
 * - They are not decisions (decisions stand alone)
 */
function areThoughtsRelated(
  prev: ThoughtChainItem,
  current: ThoughtChainItem,
  index: number,
  prevIndex: number
): boolean {
  // Must be from same agent
  if (prev.agentType !== current.agentType) {
    return false;
  }

  // Must be consecutive (or nearly consecutive - allow 1 gap for other event types)
  if (index - prevIndex > 2) {
    return false;
  }

  // Decisions stand alone
  if (prev.status?.toLowerCase().includes('decision') || current.status?.toLowerCase().includes('decision')) {
    return false;
  }

  // If previous thought is very short (< 50 chars), likely a continuation
  if (prev.content.length < 50) {
    return true;
  }

  // If current thought starts with continuation markers
  const continuationMarkers = [
    /^(and|also|additionally|furthermore|moreover|next|then|after)/i,
    /^\d+\./,  // numbered list
    /^[-•*]/,  // bullet point
  ];

  if (continuationMarkers.some(pattern => pattern.test(current.content.trim()))) {
    return true;
  }

  // Default: group if same agent and consecutive
  return true;
}

/**
 * Group related thoughts into chains.
 *
 * Per requirement 11.1: When orchestrator generates multiple related thoughts,
 * they should be grouped in Thought_Chains.
 *
 * Per requirement 11.2: Thought_Chains should display sequence of thoughts/tasks together.
 */
export function groupThoughtsIntoChains(thoughts: ThoughtChainItem[]): ThoughtChain[] {
  if (thoughts.length === 0) {
    return [];
  }

  const chains: ThoughtChain[] = [];
  let currentChain: ThoughtChain | null = null;

  thoughts.forEach((thought, index) => {
    const filteredThought = filterThoughtItem(thought);

    // Check if this thought should be added to current chain
    if (currentChain && currentChain.items.length > 0) {
      const lastItem = currentChain.items[currentChain.items.length - 1];
      const lastIndex = thoughts.findIndex(t => t.id === lastItem.id);

      if (areThoughtsRelated(lastItem, thought, index, lastIndex)) {
        // Add to current chain
        currentChain.items.push(filteredThought);
        return;
      }
    }

    // Start new chain
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

  // Add final chain
  if (currentChain && currentChain.items.length > 0) {
    chains.push(currentChain);
  }

  return chains;
}

/**
 * Check if a chain should be rendered as a single thought or as a chain.
 * Single thoughts (chains with 1 item) can be rendered with ThoughtBlock.
 * Multi-item chains should be rendered with ThoughtChain component.
 */
export function shouldRenderAsChain(chain: ThoughtChain): boolean {
  return chain.items.length > 1;
}
