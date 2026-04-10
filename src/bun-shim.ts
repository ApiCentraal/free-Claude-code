/**
 * Compatibility shim for code paths that cannot import `bun:bundle`.
 * External or recovery builds can import this helper instead.
 */
export function feature(_flag: string): boolean {
  return false
}

