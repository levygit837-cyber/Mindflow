import wrapAnsiNpm from 'wrap-ansi';

type WrapAnsiOptions = {
  hard?: boolean;
  wordWrap?: boolean;
  trim?: boolean;
};

/**
 * Wrap ANSI text with support for escape codes.
 * Uses wrap-ansi npm package for the implementation.
 */
export const wrapAnsi: (
  input: string,
  columns: number,
  options?: WrapAnsiOptions,
) => string = wrapAnsiNpm;
