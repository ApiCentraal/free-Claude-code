/**
 * Recovery fallback for generated settings types.
 * This keeps type-only imports stable in trimmed forks.
 */
export type Settings = Record<string, unknown>

