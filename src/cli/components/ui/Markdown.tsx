/**
 * Markdown - Simple markdown renderer for MindFlow CLI
 * Supports: bold, italic, code, code blocks, lists, headers
 */

import React from 'react';
import { Box, Text } from 'ink';

interface MarkdownProps {
  content: string;
  maxWidth?: number;
}

// Simple markdown parser
export const Markdown: React.FC<MarkdownProps> = ({
  content,
  maxWidth = 80,
}) => {
  const lines = content.split('\n');

  const renderLine = (line: string, index: number): React.ReactNode => {
    // Empty line
    if (!line.trim()) {
      return <Box key={index} height={1} />;
    }

    // Headers
    if (line.startsWith('# ')) {
      return (
        <Box key={index} marginY={1}>
          <Text bold color="#0D6E6E">{line.slice(2)}</Text>
        </Box>
      );
    }
    if (line.startsWith('## ')) {
      return (
        <Box key={index} marginY={1}>
          <Text bold color="#14B8A6">{line.slice(3)}</Text>
        </Box>
      );
    }
    if (line.startsWith('### ')) {
      return (
        <Box key={index} marginY={1}>
          <Text bold color="#5EEAD4">{line.slice(4)}</Text>
        </Box>
      );
    }

    // Code blocks
    if (line.startsWith('```')) {
      return (
        <Box key={index}>
          <Text color="gray" dimColor>▓ Code block</Text>
        </Box>
      );
    }

    // Inline code
    const codeRegex = /`([^`]+)`/g;
    if (codeRegex.test(line)) {
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      let match;
      codeRegex.lastIndex = 0;
      
      while ((match = codeRegex.exec(line)) !== null) {
        if (match.index > lastIndex) {
          parts.push(<Text key={`text-${lastIndex}`}>{line.slice(lastIndex, match.index)}</Text>);
        }
        parts.push(
          <Text key={`code-${match.index}`} color="#14B8A6" backgroundColor="#1A1A1A">
            {match[1]}
          </Text>
        );
        lastIndex = match.index + match[0].length;
      }
      
      if (lastIndex < line.length) {
        parts.push(<Text key={`text-${lastIndex}`}>{line.slice(lastIndex)}</Text>);
      }

      return (
        <Box key={index}>
          {parts}
        </Box>
      );
    }

    // Bold
    const boldRegex = /\*\*([^*]+)\*\*|__([^_]+)__/g;
    if (boldRegex.test(line)) {
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      let match;
      boldRegex.lastIndex = 0;
      
      while ((match = boldRegex.exec(line)) !== null) {
        if (match.index > lastIndex) {
          parts.push(<Text key={`text-${lastIndex}`}>{line.slice(lastIndex, match.index)}</Text>);
        }
        parts.push(
          <Text key={`bold-${match.index}`} bold>
            {match[1] || match[2]}
          </Text>
        );
        lastIndex = match.index + match[0].length;
      }
      
      if (lastIndex < line.length) {
        parts.push(<Text key={`text-${lastIndex}`}>{line.slice(lastIndex)}</Text>);
      }

      return (
        <Box key={index}>
          {parts}
        </Box>
      );
    }

    // Italic
    const italicRegex = /\*([^*]+)\*|_([^_]+)_/g;
    if (italicRegex.test(line)) {
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      let match;
      italicRegex.lastIndex = 0;
      
      while ((match = italicRegex.exec(line)) !== null) {
        if (match.index > lastIndex) {
          parts.push(<Text key={`text-${lastIndex}`}>{line.slice(lastIndex, match.index)}</Text>);
        }
        parts.push(
          <Text key={`italic-${match.index}`} dimColor>
            {match[1] || match[2]}
          </Text>
        );
        lastIndex = match.index + match[0].length;
      }
      
      if (lastIndex < line.length) {
        parts.push(<Text key={`text-${lastIndex}`}>{line.slice(lastIndex)}</Text>);
      }

      return (
        <Box key={index}>
          {parts}
        </Box>
      );
    }

    // Lists
    if (line.match(/^\s*[-*]\s/)) {
      return (
        <Box key={index} paddingLeft={2}>
          <Text color="#0D6E6E">• </Text>
          <Text>{line.replace(/^\s*[-*]\s/, '')}</Text>
        </Box>
      );
    }
    if (line.match(/^\s*\d+\.\s/)) {
      return (
        <Box key={index} paddingLeft={2}>
          <Text color="#0D6E6E">{line.match(/^\s*(\d+)\.\s/)?.[1]}. </Text>
          <Text>{line.replace(/^\s*\d+\.\s/, '')}</Text>
        </Box>
      );
    }

    // Links [text](url)
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    if (linkRegex.test(line)) {
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      let match;
      linkRegex.lastIndex = 0;
      
      while ((match = linkRegex.exec(line)) !== null) {
        if (match.index > lastIndex) {
          parts.push(<Text key={`text-${lastIndex}`}>{line.slice(lastIndex, match.index)}</Text>);
        }
        parts.push(
          <Text key={`link-${match.index}`} color="#3B82F6" underline>
            {match[1]}
          </Text>
        );
        lastIndex = match.index + match[0].length;
      }
      
      if (lastIndex < line.length) {
        parts.push(<Text key={`text-${lastIndex}`}>{line.slice(lastIndex)}</Text>);
      }

      return (
        <Box key={index}>
          {parts}
        </Box>
      );
    }

    // Regular line
    return (
      <Box key={index}>
        <Text>{line}</Text>
      </Box>
    );
  };

  return (
    <Box flexDirection="column" width={maxWidth}>
      {lines.map((line, index) => renderLine(line, index))}
    </Box>
  );
};

// Code block component with syntax highlighting simulation
interface CodeBlockProps {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({
  code,
  language,
  showLineNumbers = true,
}) => {
  const lines = code.split('\n');
  const maxLineNumWidth = String(lines.length).length;

  return (
    <Box 
      flexDirection="column" 
      borderStyle="single"
      borderColor="#0D6E6E"
      paddingX={1}
    >
      {language && (
        <Box marginBottom={1}>
          <Text color="gray" dimColor>▓ {language}</Text>
        </Box>
      )}
      {lines.map((line, index) => (
        <Box key={index}>
          {showLineNumbers && (
            <Text color="gray" dimColor>
              {String(index + 1).padStart(maxLineNumWidth, ' ')} │ 
            </Text>
          )}
          <Text color="#14B8A6">{line}</Text>
        </Box>
      ))}
    </Box>
  );
};

export default Markdown;
