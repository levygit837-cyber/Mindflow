/**
 * Parser for message content with ### markers
 * Parses special markers like ### Thinking, ### Tool Call, etc.
 * Also handles markdown code blocks with triple backticks
 */

import { MessageBlock, MessageBlockType, ParsedMessageContent } from '../types/messageParser';

// Pattern to match ### markers
const MARKER_PATTERN = /^###\s+(\w+)(?:\s+(.*))?$/gm;

// Mapping of marker names to block types
const MARKER_TYPE_MAP: Record<string, MessageBlockType> = {
  thinking: 'thinking',
  thought: 'thinking',
  tool: 'tool_call',
  'tool call': 'tool_call',
  'tool-call': 'tool_call',
  delegation: 'delegation',
  code: 'code',
  error: 'error',
  warning: 'warning',
  info: 'info',
  success: 'success',
};

/**
 * Parse message content and extract blocks marked with ###
 * Also extracts markdown code blocks
 */
export function parseMessageContent(content: string): ParsedMessageContent {
  const blocks: MessageBlock[] = [];
  const lines = content.split('\n');

  let currentBlock: MessageBlock | null = null;
  let currentContent: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const markerMatch = line.match(/^###\s+(\w+)(?:\s+(.*))?$/);
    const codeBlockMatch = line.match(/^```(\w+)?$/);

    if (markerMatch) {
      // Save previous block if exists
      if (currentBlock) {
        currentBlock.content = currentContent.join('\n').trim();
        if (currentBlock.content) {
          blocks.push(currentBlock);
        }
      }

      // Start new block
      const markerName = markerMatch[1].toLowerCase();
      const metadata = markerMatch[2] || '';
      const blockType = MARKER_TYPE_MAP[markerName] || 'plain';

      currentBlock = {
        type: blockType,
        content: '',
        metadata: metadata ? { title: metadata } : undefined,
      };
      currentContent = [];
    } else if (codeBlockMatch) {
      // Handle markdown code block
      const language = codeBlockMatch[1] || 'text';
      
      // Save previous block if exists
      if (currentBlock) {
        currentBlock.content = currentContent.join('\n').trim();
        if (currentBlock.content) {
          blocks.push(currentBlock);
        }
      }

      // Extract code block content
      let codeContent = '';
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeContent += lines[i] + '\n';
        i++;
      }
      
      blocks.push({
        type: 'code',
        content: codeContent.trim(),
        metadata: { title: language },
      });
      
      currentBlock = null;
      currentContent = [];
    } else if (currentBlock) {
      currentContent.push(line);
    } else {
      // Plain text before any marker
      if (line.trim()) {
        blocks.push({
          type: 'plain',
          content: line.trim(),
        });
      }
    }
  }

  // Save last block
  if (currentBlock) {
    currentBlock.content = currentContent.join('\n').trim();
    if (currentBlock.content) {
      blocks.push(currentBlock);
    }
  }

  return { blocks };
}

/**
 * Check if content contains any ### markers
 */
export function hasMarkers(content: string): boolean {
  return MARKER_PATTERN.test(content);
}

/**
 * Get marker type from a line
 */
export function getMarkerType(line: string): MessageBlockType | null {
  const match = line.match(/^###\s+(\w+)/);
  if (!match) return null;
  
  const markerName = match[1].toLowerCase();
  return MARKER_TYPE_MAP[markerName] || 'plain';
}
