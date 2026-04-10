/*---------------------------------------------------------------------------------------------
 * Recovery-compatible message contracts.
 *--------------------------------------------------------------------------------------------*/

export interface BaseMessage {
  type: string
  uuid: string
  timestamp: string
  [key: string]: unknown
}

export interface UserMessage extends BaseMessage {
  type: 'user'
  isMeta?: boolean
  message: {
    role?: 'user'
    content: unknown
    [key: string]: unknown
  }
}

export interface AssistantMessage extends BaseMessage {
  type: 'assistant'
  message: {
    id?: string
    role?: 'assistant'
    content: unknown
    model?: string
    stop_reason?: string | null
    usage?: unknown
    [key: string]: unknown
  }
}

export interface SystemMessage extends BaseMessage {
  type: 'system'
  subtype?: string
  level?: string
  content?: string
}

export type AttachmentMessage = BaseMessage
export type CollapsedReadSearchGroup = BaseMessage
export type GroupedToolUseMessage = BaseMessage
export type HookResultMessage = BaseMessage
export type MessageOrigin = Record<string, unknown>
export type NormalizedAssistantMessage = AssistantMessage
export type NormalizedMessage = Message
export type NormalizedUserMessage = UserMessage
export type PartialCompactDirection = Record<string, unknown>
export type ProgressMessage = BaseMessage
export type RenderableMessage = Message
export type RequestStartEvent = Record<string, unknown>
export type StopHookInfo = Record<string, unknown>
export type StreamEvent = Record<string, unknown>
export type SystemAgentsKilledMessage = SystemMessage
export type SystemAPIErrorMessage = SystemMessage
export type SystemApiMetricsMessage = SystemMessage
export type SystemAwaySummaryMessage = SystemMessage
export type SystemBridgeStatusMessage = SystemMessage
export type SystemCompactBoundaryMessage = SystemMessage & {
  subtype: 'compact_boundary'
}
export type SystemInformationalMessage = SystemMessage
export type SystemLocalCommandMessage = SystemMessage
export type SystemMemorySavedMessage = SystemMessage
export type SystemMessageLevel = 'info' | 'warning' | 'error' | string
export type SystemMicrocompactBoundaryMessage = SystemMessage
export type SystemPermissionRetryMessage = SystemMessage
export type SystemScheduledTaskFireMessage = SystemMessage
export type SystemStopHookSummaryMessage = SystemMessage
export type SystemThinkingMessage = SystemMessage
export type SystemTurnDurationMessage = SystemMessage
export type TombstoneMessage = BaseMessage
export type ToolUseSummaryMessage = BaseMessage

export type Message = UserMessage | AssistantMessage | SystemMessage | BaseMessage

