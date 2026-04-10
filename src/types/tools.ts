/*---------------------------------------------------------------------------------------------
 * Recovery-compatible tool progress contracts.
 *--------------------------------------------------------------------------------------------*/

export interface ToolProgressBase {
  type?: string
  status?: string
  message?: string
  timestamp?: string
  [key: string]: unknown
}

export type AgentToolProgress = ToolProgressBase
export type BashProgress = ToolProgressBase
export type MCPProgress = ToolProgressBase
export type PowerShellProgress = ToolProgressBase
export type REPLToolProgress = ToolProgressBase
export type SdkWorkflowProgress = ToolProgressBase
export type ShellProgress = ToolProgressBase
export type SkillToolProgress = ToolProgressBase
export type TaskOutputProgress = ToolProgressBase
export type ToolProgressData = ToolProgressBase
export type WebSearchProgress = ToolProgressBase

