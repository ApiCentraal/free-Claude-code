/**
 * QuerySource labels where requests originate from.
 * Keep this permissive for recovery builds while still documenting known values.
 */
export type QuerySource =
  | 'repl_main_thread'
  | 'sdk'
  | 'agent:custom'
  | 'agent:default'
  | 'agent:builtin'
  | 'compact'
  | 'session_memory'
  | 'auto_mode'
  | 'side_question'
  | 'hook_agent'
  | 'hook_prompt'
  | 'verification_agent'
  | `repl_main_thread:${string}`
  | `agent:${string}`
  | (string & {})

