/**
 * FileEditPreview - Diff view for file edits
 * Shows before/after comparison
 */

import React, { useState } from 'react';
import { Box, Text } from 'ink';

interface FileEditPreviewProps {
  filePath: string;
  originalContent: string;
  newContent: string;
  onAccept: () => void;
  onReject: () => void;
}

// Simple diff computation
interface DiffLine {
  type: 'added' | 'removed' | 'unchanged';
  content: string;
  lineNum: number;
}

const computeDiff = (original: string, modified: string): DiffLine[] => {
  const origLines = original.split('\n');
  const modLines = modified.split('\n');
  const diff: DiffLine[] = [];
  
  let origIdx = 0;
  let modIdx = 0;
  
  while (origIdx < origLines.length || modIdx < modLines.length) {
    const origLine = origLines[origIdx];
    const modLine = modLines[modIdx];
    
    if (origLine === modLine) {
      diff.push({
        type: 'unchanged',
        content: origLine,
        lineNum: origIdx + 1,
      });
      origIdx++;
      modIdx++;
    } else if (modIdx < modLines.length && (origIdx >= origLines.length || !origLines.includes(modLine))) {
      // Line added
      diff.push({
        type: 'added',
        content: modLine,
        lineNum: modIdx + 1,
      });
      modIdx++;
    } else if (origIdx < origLines.length && (modIdx >= modLines.length || !modLines.includes(origLine))) {
      // Line removed
      diff.push({
        type: 'removed',
        content: origLine,
        lineNum: origIdx + 1,
      });
      origIdx++;
    } else {
      // Modified line (treat as remove + add)
      diff.push({
        type: 'removed',
        content: origLine,
        lineNum: origIdx + 1,
      });
      diff.push({
        type: 'added',
        content: modLine,
        lineNum: modIdx + 1,
      });
      origIdx++;
      modIdx++;
    }
  }
  
  return diff;
};

export const FileEditPreview: React.FC<FileEditPreviewProps> = ({
  filePath,
  originalContent,
  newContent,
  onAccept,
  onReject,
}) => {
  const [viewMode, setViewMode] = useState<'diff' | 'side-by-side'>('diff');
  const [scrollOffset, setScrollOffset] = useState(0);
  
  const diff = computeDiff(originalContent, newContent);
  const addedCount = diff.filter(d => d.type === 'added').length;
  const removedCount = diff.filter(d => d.type === 'removed').length;

  const visibleDiff = diff.slice(scrollOffset, scrollOffset + 20);

  const getLineColor = (type: DiffLine['type']): string => {
    switch (type) {
      case 'added': return '#22C55E';
      case 'removed': return '#EF4444';
      default: return 'white';
    }
  };

  const getLinePrefix = (type: DiffLine['type']): string => {
    switch (type) {
      case 'added': return '+';
      case 'removed': return '-';
      default: return ' ';
    }
  };

  return (
    <Box 
      flexDirection="column" 
      borderStyle="double"
      borderColor="#0D6E6E"
      paddingX={2}
      paddingY={1}
    >
      {/* Header */}
      <Box marginBottom={1} justifyContent="space-between">
        <Box>
          <Text color="#0D6E6E" bold>✎ File Edit Preview</Text>
          <Text color="gray">{' • '}{filePath}</Text>
        </Box>
        <Box>
          <Text color="#22C55E">+{addedCount}</Text>
          <Text color="gray">{' / '}</Text>
          <Text color="#EF4444">-{removedCount}</Text>
        </Box>
      </Box>

      {/* View mode indicator */}
      <Box marginBottom={1}>
        <Text color="gray">View: </Text>
        <Text color={viewMode === 'diff' ? '#0D6E6E' : 'gray'}>[D] Diff </Text>
        <Text color={viewMode === 'side-by-side' ? '#0D6E6E' : 'gray'}>[S] Side-by-side</Text>
      </Box>

      {/* Diff content */}
      <Box 
        flexDirection="column" 
        borderStyle="single"
        borderColor="gray"
        paddingX={1}
        height={20}
      >
        {visibleDiff.map((line, idx) => (
          <Box key={idx}>
            <Text color="gray" dimColor>
              {String(line.lineNum).padStart(4, ' ')} 
            </Text>
            <Text color={getLineColor(line.type)}>
              {getLinePrefix(line.type)} {line.content.slice(0, 70)}
            </Text>
          </Box>
        ))}
      </Box>

      {/* Scroll indicator */}
      {scrollOffset > 0 && (
        <Box marginTop={1}>
          <Text color="gray" dimColor>▲ Scroll up (↑)</Text>
        </Box>
      )}
      {scrollOffset + 20 < diff.length && (
        <Box>
          <Text color="gray" dimColor>▼ Scroll down (↓)</Text>
        </Box>
      )}

      {/* Actions */}
      <Box marginTop={1} justifyContent="space-between">
        <Box>
          <Text color="#22C55E">[Y] Accept</Text>
          <Text color="gray">{' • '}</Text>
          <Text color="#EF4444">[N] Reject</Text>
        </Box>
        <Box>
          <Text color="gray" dimColor>
            {scrollOffset + 1}-{Math.min(scrollOffset + 20, diff.length)} of {diff.length}
          </Text>
        </Box>
      </Box>
    </Box>
  );
};

// Inline diff for small changes
interface InlineDiffProps {
  original: string;
  modified: string;
  context?: number;
}

export const InlineDiff: React.FC<InlineDiffProps> = ({
  original,
  modified,
  context = 3,
}) => {
  const diff = computeDiff(original, modified);
  
  // Find changed regions
  const changedIndices = diff
    .map((line, idx) => ({ line, idx }))
    .filter(({ line }) => line.type !== 'unchanged')
    .map(({ idx }) => idx);
  
  if (changedIndices.length === 0) {
    return (
      <Box>
        <Text color="gray">(No changes)</Text>
      </Box>
    );
  }

  // Show context around changes
  const contextLines = new Set<number>();
  changedIndices.forEach(idx => {
    for (let i = Math.max(0, idx - context); i <= Math.min(diff.length - 1, idx + context); i++) {
      contextLines.add(i);
    }
  });

  const visibleIndices = Array.from(contextLines).sort((a, b) => a - b);

  return (
    <Box flexDirection="column">
      {visibleIndices.map((idx) => {
        const line = diff[idx];
        const showEllipsis = idx > 0 && !contextLines.has(idx - 1);
        
        return (
          <Box key={idx}>
            {showEllipsis && (
              <Box>
                <Text color="gray" dimColor>...</Text>
              </Box>
            )}
            <Box>
              <Text color="gray" dimColor>
                {String(line.lineNum).padStart(3, ' ')}
              </Text>
              <Text 
                color={line.type === 'added' ? '#22C55E' : line.type === 'removed' ? '#EF4444' : 'white'}
              >
                {' '}{line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
                {' '}{line.content.slice(0, 60)}
              </Text>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
};

export default FileEditPreview;
