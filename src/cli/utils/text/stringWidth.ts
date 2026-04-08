import { getGraphemeSegmenter } from './intl.js';

/**
 * JavaScript implementation of stringWidth for MindFlow CLI.
 *
 * Get the display width of a string as it would appear in a terminal.
 *
 * This implementation handles:
 * - ANSI escape codes (stripped before calculation)
 * - East Asian wide characters (CJK)
 * - Emoji and grapheme clusters
 * - Zero-width characters
 */

function stringWidthImpl(str: string): number {
  if (typeof str !== 'string' || str.length === 0) {
    return 0;
  }

  // Fast path: pure ASCII string (no ANSI codes, no wide chars)
  let isPureAscii = true;
  for (let i = 0; i < str.length; i++) {
    const code = str.charCodeAt(i);
    // Check for non-ASCII or ANSI escape (0x1b)
    if (code >= 127 || code === 0x1b) {
      isPureAscii = false;
      break;
    }
  }
  if (isPureAscii) {
    // Count printable characters (exclude control chars)
    let width = 0;
    for (let i = 0; i < str.length; i++) {
      const code = str.charCodeAt(i);
      if (code > 0x1f) {
        width++;
      }
    }
    return width;
  }

  // Strip ANSI if escape character is present
  if (str.includes('\x1b')) {
    str = stripAnsi(str);
    if (str.length === 0) {
      return 0;
    }
  }

  // Fast path: simple Unicode (no emoji, variation selectors, or joiners)
  if (!needsSegmentation(str)) {
    let width = 0;
    for (const char of str) {
      const codePoint = char.codePointAt(0)!;
      if (!isZeroWidth(codePoint)) {
        width += getEastAsianWidth(codePoint);
      }
    }
    return width;
  }

  let width = 0;

  for (const { segment: grapheme } of getGraphemeSegmenter().segment(str)) {
    // Calculate width for grapheme clusters
    // For grapheme clusters, only count the first non-zero-width character's width
    for (const char of grapheme) {
      const codePoint = char.codePointAt(0)!;
      if (!isZeroWidth(codePoint)) {
        width += getEastAsianWidth(codePoint);
        break;
      }
    }
  }

  return width;
}

function needsSegmentation(str: string): boolean {
  for (const char of str) {
    const cp = char.codePointAt(0)!;
    // Emoji ranges
    if (cp >= 0x1f300 && cp <= 0x1faff) return true;
    if (cp >= 0x2600 && cp <= 0x27bf) return true;
    if (cp >= 0x1f1e6 && cp <= 0x1f1ff) return true;
    // Variation selectors, ZWJ
    if (cp >= 0xfe00 && cp <= 0xfe0f) return true;
    if (cp === 0x200d) return true;
  }
  return false;
}

function getEastAsianWidth(codePoint: number): number {
  // Simplified East Asian Width calculation
  // Fullwidth and Wide characters = 2
  // All others = 1
  
  // CJK Unified Ideographs
  if (codePoint >= 0x4e00 && codePoint <= 0x9fff) return 2;
  // CJK Extensions
  if (codePoint >= 0x3400 && codePoint <= 0x4dbf) return 2;
  if (codePoint >= 0x20000 && codePoint <= 0x2a6df) return 2;
  if (codePoint >= 0x2a700 && codePoint <= 0x2b73f) return 2;
  if (codePoint >= 0x2b740 && codePoint <= 0x2b81f) return 2;
  if (codePoint >= 0x2b820 && codePoint <= 0x2ceaf) return 2;
  if (codePoint >= 0xf900 && codePoint <= 0xfaff) return 2;
  // Fullwidth forms
  if (codePoint >= 0xff01 && codePoint <= 0xff60) return 2;
  if (codePoint >= 0xffe0 && codePoint <= 0xffe6) return 2;
  // Hangul Jamo
  if (codePoint >= 0x1100 && codePoint <= 0x11ff) return 2;
  if (codePoint >= 0x3130 && codePoint <= 0x318f) return 2;
  if (codePoint >= 0xa960 && codePoint <= 0xa97f) return 2;
  if (codePoint >= 0xac00 && codePoint <= 0xd7af) return 2;
  // Katakana/Hiragana
  if (codePoint >= 0x3040 && codePoint <= 0x30ff) return 2;
  if (codePoint >= 0x31f0 && codePoint <= 0x31ff) return 2;
  
  return 1;
}

function isZeroWidth(codePoint: number): boolean {
  // Fast path for common printable range
  if (codePoint >= 0x20 && codePoint < 0x7f) return false;
  if (codePoint >= 0xa0 && codePoint < 0x0300) return codePoint === 0x00ad;

  // Control characters
  if (codePoint <= 0x1f || (codePoint >= 0x7f && codePoint <= 0x9f)) return true;

  // Zero-width and invisible characters
  if (
    (codePoint >= 0x200b && codePoint <= 0x200d) || // ZW space/joiner
    codePoint === 0xfeff || // BOM
    (codePoint >= 0x2060 && codePoint <= 0x2064) // Word joiner etc.
  ) {
    return true;
  }

  // Variation selectors
  if (
    (codePoint >= 0xfe00 && codePoint <= 0xfe0f) ||
    (codePoint >= 0xe0100 && codePoint <= 0xe01ef)
  ) {
    return true;
  }

  // Combining diacritical marks
  if (
    (codePoint >= 0x0300 && codePoint <= 0x036f) ||
    (codePoint >= 0x1ab0 && codePoint <= 0x1aff) ||
    (codePoint >= 0x1dc0 && codePoint <= 0x1dff) ||
    (codePoint >= 0x20d0 && codePoint <= 0x20ff) ||
    (codePoint >= 0xfe20 && codePoint <= 0xfe2f)
  ) {
    return true;
  }

  // Surrogates, tag characters
  if (codePoint >= 0xd800 && codePoint <= 0xdfff) return true;
  if (codePoint >= 0xe0000 && codePoint <= 0xe007f) return true;

  return false;
}

/**
 * Simple ANSI escape code stripper.
 * Removes ANSI escape sequences from a string.
 */
function stripAnsi(str: string): string {
  return str.replace(/\x1b\[[0-9;]*m/g, '');
}

export const stringWidth = stringWidthImpl;
