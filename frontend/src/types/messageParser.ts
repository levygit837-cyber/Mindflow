/**
 * Types for parsing message content with ### markers
 */

export type MessageBlockType =
  | 'thinking'
  | 'tool_call'
  | 'delegation'
  | 'code'
  | 'error'
  | 'info'
  | 'warning'
  | 'success'
  | 'plain';

export interface MessageBlock {
  type: MessageBlockType;
  content: string;
  metadata?: Record<string, string>;
}

export interface ParsedMessageContent {
  blocks: MessageBlock[];
}
