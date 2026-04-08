import { stringWidth } from './stringWidth.js';
import { wrapAnsi } from './wrapAnsi.js';
import { getGraphemeSegmenter, getWordSegmenter } from './intl.js';

type WrappedText = string[];
type Position = {
  line: number;
  column: number;
};

class WrappedLine {
  constructor(
    public readonly text: string,
    public readonly startOffset: number,
    public readonly isPrecededByNewline: boolean,
    public readonly endsWithNewline: boolean = false,
  ) {}

  equals(other: WrappedLine): boolean {
    return this.text === other.text && this.startOffset === other.startOffset;
  }

  get length(): number {
    return this.text.length + (this.endsWithNewline ? 1 : 0);
  }
}

export class MeasuredText {
  private _wrappedLines?: WrappedLine[];
  public readonly text: string;
  private navigationCache: Map<string, number>;
  private graphemeBoundaries?: number[];

  constructor(
    text: string,
    readonly columns: number,
  ) {
    this.text = text.normalize('NFC');
    this.navigationCache = new Map();
  }

  /**
   * Lazily computes and caches wrapped lines.
   */
  private get wrappedLines(): WrappedLine[] {
    if (!this._wrappedLines) {
      this._wrappedLines = this.measureWrappedText();
    }
    return this._wrappedLines;
  }

  private getGraphemeBoundaries(): number[] {
    if (!this.graphemeBoundaries) {
      this.graphemeBoundaries = [];
      for (const { index } of getGraphemeSegmenter().segment(this.text)) {
        this.graphemeBoundaries.push(index);
      }
      this.graphemeBoundaries.push(this.text.length);
    }
    return this.graphemeBoundaries;
  }

  private wordBoundariesCache?: Array<{
    start: number;
    end: number;
    isWordLike: boolean;
  }>;

  public getWordBoundaries(): Array<{
    start: number;
    end: number;
    isWordLike: boolean;
  }> {
    if (!this.wordBoundariesCache) {
      this.wordBoundariesCache = [];
      for (const segment of getWordSegmenter().segment(this.text)) {
        this.wordBoundariesCache.push({
          start: segment.index,
          end: segment.index + segment.segment.length,
          isWordLike: segment.isWordLike ?? false,
        });
      }
    }
    return this.wordBoundariesCache;
  }

  private binarySearchBoundary(
    boundaries: number[],
    target: number,
    findNext: boolean,
  ): number {
    let left = 0;
    let right = boundaries.length - 1;
    let result = findNext ? this.text.length : 0;

    while (left <= right) {
      const mid = Math.floor((left + right) / 2);
      const boundary = boundaries[mid];
      if (boundary === undefined) break;

      if (findNext) {
        if (boundary > target) {
          result = boundary;
          right = mid - 1;
        } else {
          left = mid + 1;
        }
      } else {
        if (boundary < target) {
          result = boundary;
          left = mid + 1;
        } else {
          right = mid - 1;
        }
      }
    }

    return result;
  }

  public stringIndexToDisplayWidth(text: string, index: number): number {
    if (index <= 0) return 0;
    if (index >= text.length) return stringWidth(text);
    return stringWidth(text.substring(0, index));
  }

  public displayWidthToStringIndex(text: string, targetWidth: number): number {
    if (targetWidth <= 0) return 0;
    if (!text) return 0;

    if (text === this.text) {
      return this.offsetAtDisplayWidth(targetWidth);
    }

    let currentWidth = 0;
    let currentOffset = 0;

    for (const { segment, index } of getGraphemeSegmenter().segment(text)) {
      const segmentWidth = stringWidth(segment);

      if (currentWidth + segmentWidth > targetWidth) {
        break;
      }

      currentWidth += segmentWidth;
      currentOffset = index + segment.length;
    }

    return currentOffset;
  }

  private offsetAtDisplayWidth(targetWidth: number): number {
    if (targetWidth <= 0) return 0;

    let currentWidth = 0;
    const boundaries = this.getGraphemeBoundaries();

    for (let i = 0; i < boundaries.length - 1; i++) {
      const start = boundaries[i];
      const end = boundaries[i + 1];
      if (start === undefined || end === undefined) continue;
      const segment = this.text.substring(start, end);
      const segmentWidth = stringWidth(segment);

      if (currentWidth + segmentWidth > targetWidth) {
        return start;
      }
      currentWidth += segmentWidth;
    }

    return this.text.length;
  }

  private measureWrappedText(): WrappedLine[] {
    const wrappedText = wrapAnsi(this.text, this.columns, {
      hard: true,
      trim: false,
    });

    const wrappedLines: WrappedLine[] = [];
    let searchOffset = 0;
    let lastNewLinePos = -1;

    const lines = wrappedText.split('\n');
    for (let i = 0; i < lines.length; i++) {
      const text = lines[i]!;
      const isPrecededByNewline = (startOffset: number) =>
        i === 0 || (startOffset > 0 && this.text[startOffset - 1] === '\n');

      if (text.length === 0) {
        lastNewLinePos = this.text.indexOf('\n', lastNewLinePos + 1);

        if (lastNewLinePos !== -1) {
          const startOffset = lastNewLinePos;
          const endsWithNewline = true;

          wrappedLines.push(
            new WrappedLine(
              text,
              startOffset,
              isPrecededByNewline(startOffset),
              endsWithNewline,
            ),
          );
        } else {
          const startOffset = this.text.length;
          wrappedLines.push(
            new WrappedLine(
              text,
              startOffset,
              isPrecededByNewline(startOffset),
              false,
            ),
          );
        }
      } else {
        const startOffset = this.text.indexOf(text, searchOffset);

        if (startOffset === -1) {
          throw new Error('Failed to find wrapped line in text');
        }

        searchOffset = startOffset + text.length;

        const potentialNewlinePos = startOffset + text.length;
        const endsWithNewline =
          potentialNewlinePos < this.text.length &&
          this.text[potentialNewlinePos] === '\n';

        if (endsWithNewline) {
          lastNewLinePos = potentialNewlinePos;
        }

        wrappedLines.push(
          new WrappedLine(
            text,
            startOffset,
            isPrecededByNewline(startOffset),
            endsWithNewline,
          ),
        );
      }
    }

    return wrappedLines;
  }

  public getWrappedText(): WrappedText {
    return this.wrappedLines.map(line =>
      line.isPrecededByNewline ? line.text : line.text.trimStart(),
    );
  }

  public getWrappedLines(): WrappedLine[] {
    return this.wrappedLines;
  }

  private getLine(line: number): WrappedLine {
    const lines = this.wrappedLines;
    return lines[Math.max(0, Math.min(line, lines.length - 1))]!;
  }

  public getOffsetFromPosition(position: Position): number {
    const wrappedLine = this.getLine(position.line);

    if (wrappedLine.text.length === 0 && wrappedLine.endsWithNewline) {
      return wrappedLine.startOffset;
    }

    const leadingWhitespace = wrappedLine.isPrecededByNewline
      ? 0
      : wrappedLine.text.length - wrappedLine.text.trimStart().length;

    const displayColumnWithLeading = position.column + leadingWhitespace;
    const stringIndex = this.displayWidthToStringIndex(
      wrappedLine.text,
      displayColumnWithLeading,
    );

    const offset = wrappedLine.startOffset + stringIndex;

    const lineEnd = wrappedLine.startOffset + wrappedLine.text.length;

    let maxOffset = lineEnd;
    const lineDisplayWidth = stringWidth(wrappedLine.text);
    if (wrappedLine.endsWithNewline && position.column > lineDisplayWidth) {
      maxOffset = lineEnd + 1;
    }

    return Math.min(offset, maxOffset);
  }

  public getLineLength(line: number): number {
    const wrappedLine = this.getLine(line);
    return stringWidth(wrappedLine.text);
  }

  public getPositionFromOffset(offset: number): Position {
    const lines = this.wrappedLines;
    for (let line = 0; line < lines.length; line++) {
      const currentLine = lines[line]!;
      const nextLine = lines[line + 1];
      if (
        offset >= currentLine.startOffset &&
        (!nextLine || offset < nextLine.startOffset)
      ) {
        const stringPosInLine = offset - currentLine.startOffset;

        let displayColumn: number;
        if (currentLine.isPrecededByNewline) {
          displayColumn = this.stringIndexToDisplayWidth(
            currentLine.text,
            stringPosInLine,
          );
        } else {
          const leadingWhitespace =
            currentLine.text.length - currentLine.text.trimStart().length;
          if (stringPosInLine < leadingWhitespace) {
            displayColumn = 0;
          } else {
            const trimmedText = currentLine.text.trimStart();
            const posInTrimmed = stringPosInLine - leadingWhitespace;
            displayColumn = this.stringIndexToDisplayWidth(
              trimmedText,
              posInTrimmed,
            );
          }
        }

        return {
          line,
          column: Math.max(0, displayColumn),
        };
      }
    }

    const line = lines.length - 1;
    const lastLine = this.wrappedLines[line]!;
    return {
      line,
      column: stringWidth(lastLine.text),
    };
  }

  public get lineCount(): number {
    return this.wrappedLines.length;
  }

  private withCache<T>(key: string, compute: () => T): T {
    const cached = this.navigationCache.get(key);
    if (cached !== undefined) return cached as T;

    const result = compute();
    this.navigationCache.set(key, result as number);
    return result;
  }

  nextOffset(offset: number): number {
    return this.withCache(`next:${offset}`, () => {
      const boundaries = this.getGraphemeBoundaries();
      return this.binarySearchBoundary(boundaries, offset, true);
    });
  }

  prevOffset(offset: number): number {
    if (offset <= 0) return 0;

    return this.withCache(`prev:${offset}`, () => {
      const boundaries = this.getGraphemeBoundaries();
      return this.binarySearchBoundary(boundaries, offset, false);
    });
  }

  snapToGraphemeBoundary(offset: number): number {
    if (offset <= 0) return 0;
    if (offset >= this.text.length) return this.text.length;
    const boundaries = this.getGraphemeBoundaries();
    let lo = 0;
    let hi = boundaries.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (boundaries[mid]! <= offset) {
        lo = mid;
      } else {
        hi = mid - 1;
      }
    }
    return boundaries[lo]!;
  }
}

export class Cursor {
  readonly offset: number;
  constructor(
    readonly measuredText: MeasuredText,
    offset: number = 0,
    readonly selection: number = 0,
  ) {
    this.offset = Math.max(0, Math.min(this.text.length, offset));
  }

  static fromText(
    text: string,
    columns: number,
    offset: number = 0,
    selection: number = 0,
  ): Cursor {
    return new Cursor(new MeasuredText(text, columns - 1), offset, selection);
  }

  get text(): string {
    return this.measuredText.text;
  }

  getViewportStartLine(maxVisibleLines?: number): number {
    if (maxVisibleLines === undefined || maxVisibleLines <= 0) return 0;
    const { line } = this.getPosition();
    const allLines = this.measuredText.getWrappedText();
    if (allLines.length <= maxVisibleLines) return 0;
    const half = Math.floor(maxVisibleLines / 2);
    let startLine = Math.max(0, line - half);
    const endLine = Math.min(allLines.length, startLine + maxVisibleLines);
    if (endLine - startLine < maxVisibleLines) {
      startLine = Math.max(0, endLine - maxVisibleLines);
    }
    return startLine;
  }

  getViewportCharOffset(maxVisibleLines?: number): number {
    const startLine = this.getViewportStartLine(maxVisibleLines);
    if (startLine === 0) return 0;
    const wrappedLines = this.measuredText.getWrappedLines();
    return wrappedLines[startLine]?.startOffset ?? 0;
  }

  getViewportCharEnd(maxVisibleLines?: number): number {
    const startLine = this.getViewportStartLine(maxVisibleLines);
    const allLines = this.measuredText.getWrappedLines();
    if (maxVisibleLines === undefined || maxVisibleLines <= 0)
      return this.text.length;
    const endLine = Math.min(allLines.length, startLine + maxVisibleLines);
    if (endLine >= allLines.length) return this.text.length;
    return allLines[endLine]?.startOffset ?? this.text.length;
  }

  render(
    cursorChar: string,
    mask: string,
    invert: (text: string) => string,
    maxVisibleLines?: number,
  ) {
    const { line, column } = this.getPosition();
    const allLines = this.measuredText.getWrappedText();

    const startLine = this.getViewportStartLine(maxVisibleLines);
    const endLine =
      maxVisibleLines !== undefined && maxVisibleLines > 0
        ? Math.min(allLines.length, startLine + maxVisibleLines)
        : allLines.length;

    return allLines
      .slice(startLine, endLine)
      .map((text, i) => {
        const currentLine = i + startLine;
        let displayText = text;
        if (mask) {
          const graphemes = Array.from(getGraphemeSegmenter().segment(text));
          if (currentLine === allLines.length - 1) {
            const visibleCount = Math.min(6, graphemes.length);
            const maskCount = graphemes.length - visibleCount;
            const splitOffset =
              graphemes.length > visibleCount ? graphemes[maskCount]!.index : 0;
            displayText = mask.repeat(maskCount) + text.slice(splitOffset);
          } else {
            displayText = mask.repeat(graphemes.length);
          }
        }
        if (line !== currentLine) return displayText.trimEnd();

        let beforeCursor = '';
        let atCursor = cursorChar;
        let afterCursor = '';
        let currentWidth = 0;
        let cursorFound = false;

        for (const { segment } of getGraphemeSegmenter().segment(displayText)) {
          if (cursorFound) {
            afterCursor += segment;
            continue;
          }
          const nextWidth = currentWidth + stringWidth(segment);
          if (nextWidth > column) {
            atCursor = segment;
            cursorFound = true;
          } else {
            currentWidth = nextWidth;
            beforeCursor += segment;
          }
        }

        const renderedCursor = cursorChar ? invert(atCursor) : atCursor;

        return (
          beforeCursor + renderedCursor + afterCursor.trimEnd()
        );
      })
      .join('\n');
  }

  left(): Cursor {
    if (this.offset === 0) return this;
    const prevOffset = this.measuredText.prevOffset(this.offset);
    return new Cursor(this.measuredText, prevOffset);
  }

  right(): Cursor {
    if (this.offset >= this.text.length) return this;
    const nextOffset = this.measuredText.nextOffset(this.offset);
    return new Cursor(this.measuredText, Math.min(nextOffset, this.text.length));
  }

  up(): Cursor {
    const { line, column } = this.getPosition();
    if (line === 0) {
      return this;
    }

    const prevLine = this.measuredText.getWrappedText()[line - 1];
    if (prevLine === undefined) {
      return this;
    }

    const prevLineDisplayWidth = stringWidth(prevLine);
    if (column > prevLineDisplayWidth) {
      const newOffset = this.getOffset({
        line: line - 1,
        column: prevLineDisplayWidth,
      });
      return new Cursor(this.measuredText, newOffset, 0);
    }

    const newOffset = this.getOffset({ line: line - 1, column });
    return new Cursor(this.measuredText, newOffset, 0);
  }

  down(): Cursor {
    const { line, column } = this.getPosition();
    if (line >= this.measuredText.lineCount - 1) {
      return this;
    }

    const nextLine = this.measuredText.getWrappedText()[line + 1];
    if (nextLine === undefined) {
      return this;
    }

    const nextLineDisplayWidth = stringWidth(nextLine);
    if (column > nextLineDisplayWidth) {
      const newOffset = this.getOffset({
        line: line + 1,
        column: nextLineDisplayWidth,
      });
      return new Cursor(this.measuredText, newOffset, 0);
    }

    const newOffset = this.getOffset({ line: line + 1, column });
    return new Cursor(this.measuredText, newOffset, 0);
  }

  startOfLine(): Cursor {
    const { line, column } = this.getPosition();

    if (column === 0 && line > 0) {
      return new Cursor(
        this.measuredText,
        this.getOffset({
          line: line - 1,
          column: 0,
        }),
        0,
      );
    }

    return new Cursor(
      this.measuredText,
      this.getOffset({
        line,
        column: 0,
      }),
      0,
    );
  }

  endOfLine(): Cursor {
    const { line } = this.getPosition();
    const column = this.measuredText.getLineLength(line);
    const offset = this.getOffset({ line, column });
    return new Cursor(this.measuredText, offset, 0);
  }

  insert(text: string): Cursor {
    const newText = this.text.slice(0, this.offset) + text + this.text.slice(this.offset);
    const newMeasuredText = new MeasuredText(newText, this.measuredText.columns);
    const newOffset = this.offset + text.length;
    return new Cursor(newMeasuredText, newOffset);
  }

  backspace(): Cursor {
    if (this.offset === 0) return this;
    const prevOffset = this.measuredText.prevOffset(this.offset);
    const newText = this.text.slice(0, prevOffset) + this.text.slice(this.offset);
    const newMeasuredText = new MeasuredText(newText, this.measuredText.columns);
    return new Cursor(newMeasuredText, prevOffset);
  }

  del(): Cursor {
    if (this.offset >= this.text.length) return this;
    const nextOffset = this.measuredText.nextOffset(this.offset);
    const newText = this.text.slice(0, this.offset) + this.text.slice(nextOffset);
    const newMeasuredText = new MeasuredText(newText, this.measuredText.columns);
    return new Cursor(newMeasuredText, this.offset);
  }

  deleteTokenBefore(): Cursor | undefined {
    const wordBoundaries = this.measuredText.getWordBoundaries();
    for (let i = wordBoundaries.length - 1; i >= 0; i--) {
      const boundary = wordBoundaries[i]!;
      if (boundary.end === this.offset && boundary.isWordLike) {
        const newText = this.text.slice(0, boundary.start) + this.text.slice(this.offset);
        const newMeasuredText = new MeasuredText(newText, this.measuredText.columns);
        return new Cursor(newMeasuredText, boundary.start);
      }
    }
    return undefined;
  }

  deleteWordBefore(): Cursor {
    const deleted = this.deleteTokenBefore();
    if (deleted) return deleted;
    return this.backspace();
  }

  deleteWordAfter(): Cursor {
    const wordBoundaries = this.measuredText.getWordBoundaries();
    for (const boundary of wordBoundaries) {
      if (boundary.start === this.offset && boundary.isWordLike) {
        const newText = this.text.slice(0, this.offset) + this.text.slice(boundary.end);
        const newMeasuredText = new MeasuredText(newText, this.measuredText.columns);
        return new Cursor(newMeasuredText, this.offset);
      }
    }
    return this.del();
  }

  prevWord(): Cursor {
    if (this.offset === 0) return this;
    const wordBoundaries = this.measuredText.getWordBoundaries();
    for (let i = wordBoundaries.length - 1; i >= 0; i--) {
      const boundary = wordBoundaries[i]!;
      if (boundary.end < this.offset && boundary.isWordLike) {
        return new Cursor(this.measuredText, boundary.start);
      }
    }
    return new Cursor(this.measuredText, 0);
  }

  nextWord(): Cursor {
    if (this.offset >= this.text.length) return this;
    const wordBoundaries = this.measuredText.getWordBoundaries();
    for (const boundary of wordBoundaries) {
      if (boundary.start > this.offset && boundary.isWordLike) {
        return new Cursor(this.measuredText, boundary.start);
      }
    }
    return new Cursor(this.measuredText, this.text.length);
  }

  endOfWord(): Cursor {
    if (this.offset >= this.text.length) return this;
    const wordBoundaries = this.measuredText.getWordBoundaries();
    for (const boundary of wordBoundaries) {
      if (!boundary.isWordLike) continue;
      if (this.offset >= boundary.start && this.offset < boundary.end - 1) {
        return new Cursor(this.measuredText, boundary.end - 1);
      }
      if (this.offset === boundary.end - 1) {
        const nextWord = this.nextWord();
        if (nextWord.offset === this.text.length) {
          return new Cursor(this.measuredText, this.text.length);
        }
        return nextWord.endOfWord();
      }
    }
    return this;
  }

  getPosition(): Position {
    return this.measuredText.getPositionFromOffset(this.offset);
  }

  getOffset(position: Position): number {
    return this.measuredText.getOffsetFromPosition(position);
  }

  isAtStart(): boolean {
    return this.offset === 0;
  }

  isAtEnd(): boolean {
    return this.offset >= this.text.length;
  }

  equals(other: Cursor): boolean {
    return this.offset === other.offset && this.text === other.text;
  }
}
