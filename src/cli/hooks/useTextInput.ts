import { useState, useCallback, useEffect } from 'react';
import { Cursor } from '../utils/text/Cursor.js';
import { useMessageStore } from '../core/MessageStore.js';

export type UseTextInputProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: (value: string) => void;
  onExit?: () => void;
  columns: number;
  maxVisibleLines?: number;
  cursorChar?: string;
  mask?: string;
  invert?: (text: string) => string;
};

export type TextInputState = {
  onInput: (input: string, key: any) => void;
  renderedValue: string;
  cursorLine: number;
  cursorColumn: number;
  offset: number;
  setOffset: (offset: number) => void;
};

export function useTextInput({
  value: originalValue,
  onChange,
  onSubmit,
  onExit,
  columns,
  maxVisibleLines,
  cursorChar = '▋',
  mask = '',
  invert = (text: string) => text,
}: UseTextInputProps): TextInputState {
  console.log('useTextInput hook called with:', { originalValue, columns });
  const [offset, setOffset] = useState(0);
  const [text, setText] = useState(originalValue);
  const { inputHistory, setInputValue, isLoading } = useMessageStore();
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Sync local text with parent value
  useEffect(() => {
    setText(originalValue);
  }, [originalValue]);

  const handleInput = useCallback((inputChar: string, key: any) => {
    console.log('Input received:', { inputChar, key, isLoading, text, offset });
    if (isLoading) {
      console.log('Input blocked - isLoading is true');
      return;
    }

    // Log all key properties for debugging
    console.log('Key object:', JSON.stringify(key));

    // Create cursor with current state
    const currentCursor = Cursor.fromText(text, columns, offset);

    // Handle Enter to submit
    if (key.return) {
      if (text.trim()) {
        onSubmit?.(text);
        // Add to history
        if (!inputHistory.length || inputHistory[inputHistory.length - 1] !== text) {
          useMessageStore.setState((state: { inputHistory: string[] }) => ({
            inputHistory: [...state.inputHistory, text],
          }));
        }
        onChange('');
        setText('');
        setOffset(0);
        setHistoryIndex(-1);
      }
      return;
    }

    // Handle arrow up/down for history
    if (key.upArrow) {
      const newIndex = historyIndex === -1
        ? inputHistory.length - 1
        : Math.max(0, historyIndex - 1);

      if (newIndex >= 0 && newIndex < inputHistory.length) {
        const historyItem = inputHistory[newIndex];
        setText(historyItem);
        onChange(historyItem);
        setOffset(historyItem.length);
        setHistoryIndex(newIndex);
      }
      return;
    }

    if (key.downArrow) {
      const newIndex = historyIndex === -1
        ? -1
        : historyIndex + 1;

      if (newIndex >= inputHistory.length) {
        setText('');
        onChange('');
        setOffset(0);
        setHistoryIndex(-1);
      } else if (newIndex >= 0) {
        const historyItem = inputHistory[newIndex];
        setText(historyItem);
        onChange(historyItem);
        setOffset(historyItem.length);
        setHistoryIndex(newIndex);
      }
      return;
    }

    // Handle left/right arrows for cursor movement
    if (key.leftArrow) {
      const newCursor = currentCursor.left();
      setOffset(newCursor.offset);
      return;
    }

    if (key.rightArrow) {
      const newCursor = currentCursor.right();
      setOffset(newCursor.offset);
      return;
    }

    // Handle up/down for multi-line cursor movement
    if (key.upArrow && !key.ctrl) {
      const newCursor = currentCursor.up();
      setOffset(newCursor.offset);
      return;
    }

    if (key.downArrow && !key.ctrl) {
      const newCursor = currentCursor.down();
      setOffset(newCursor.offset);
      return;
    }

    // Handle backspace
    console.log('Checking backspace:', { key });
    if (key.backspace || key.backspace === true || inputChar === '\b' || inputChar === '\x7f') {
      console.log('Backspace detected', { text, offset, isLoading, key });
      const newCursor = currentCursor.backspace();
      console.log('Backspace result', { newText: newCursor.text, newOffset: newCursor.offset });
      setText(newCursor.text);
      onChange(newCursor.text);
      setOffset(newCursor.offset);
      setHistoryIndex(-1);
      return;
    }

    // Handle delete
    if (key.delete) {
      const newCursor = currentCursor.del();
      setText(newCursor.text);
      onChange(newCursor.text);
      setOffset(newCursor.offset);
      setHistoryIndex(-1);
      return;
    }

    // Handle Ctrl+Left/Right for word movement
    if (key.ctrl && key.leftArrow) {
      const newCursor = currentCursor.prevWord();
      setOffset(newCursor.offset);
      return;
    }

    if (key.ctrl && key.rightArrow) {
      const newCursor = currentCursor.nextWord();
      setOffset(newCursor.offset);
      return;
    }

    // Handle Ctrl+Backspace/Delete for word deletion
    if (key.ctrl && key.backspace) {
      const newCursor = currentCursor.deleteWordBefore();
      setText(newCursor.text);
      onChange(newCursor.text);
      setOffset(newCursor.offset);
      setHistoryIndex(-1);
      return;
    }

    if (key.ctrl && key.delete) {
      const newCursor = currentCursor.deleteWordAfter();
      setText(newCursor.text);
      onChange(newCursor.text);
      setOffset(newCursor.offset);
      setHistoryIndex(-1);
      return;
    }

    // Handle Home/End
    if (key.home) {
      const newCursor = currentCursor.startOfLine();
      setOffset(newCursor.offset);
      return;
    }

    if (key.end) {
      const newCursor = currentCursor.endOfLine();
      setOffset(newCursor.offset);
      return;
    }

    // Handle Ctrl+C (exit)
    if (key.ctrl && inputChar === 'c') {
      onExit?.();
      return;
    }

    // Handle Ctrl+L (clear)
    if (key.ctrl && inputChar === 'l') {
      // Clear screen - let the caller handle this
      return;
    }

    // Handle Ctrl+U (clear to start of line)
    if (key.ctrl && inputChar === 'u') {
      const { line } = currentCursor.getPosition();
      const startOffset = currentCursor.getOffset({ line, column: 0 });
      const newText = currentCursor.text.slice(startOffset);
      setText(newText);
      onChange(newText);
      setOffset(0);
      setHistoryIndex(-1);
      return;
    }

    // Handle Ctrl+K (clear to end of line)
    if (key.ctrl && inputChar === 'k') {
      const newText = currentCursor.text.slice(0, currentCursor.offset);
      setText(newText);
      onChange(newText);
      setOffset(currentCursor.offset);
      setHistoryIndex(-1);
      return;
    }

    // Handle regular character input
    if (inputChar && !key.ctrl && !key.meta) {
      const newCursor = currentCursor.insert(inputChar);
      setText(newCursor.text);
      onChange(newCursor.text);
      setOffset(newCursor.offset);
      setHistoryIndex(-1);
    }
  }, [text, columns, offset, onChange, onSubmit, onExit, isLoading, inputHistory, historyIndex]);

  // Sync with MessageStore
  useEffect(() => {
    setInputValue(text);
  }, [text, setInputValue]);

  // Create cursor for rendering
  const renderCursor = Cursor.fromText(text, columns, offset);
  const { line, column } = renderCursor.getPosition();
  const viewportStartLine = renderCursor.getViewportStartLine(maxVisibleLines);

  console.log('useTextInput returning onInput function');
  return {
    onInput: handleInput,
    renderedValue: renderCursor.render(
      cursorChar,
      mask,
      invert,
      maxVisibleLines,
    ),
    offset,
    setOffset,
    cursorLine: line - viewportStartLine,
    cursorColumn: column,
  };
}
