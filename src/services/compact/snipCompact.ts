import { randomUUID } from 'crypto'
import type { Message } from '../../types/message.js'
import { isEnvTruthy } from '../../utils/envUtils.js'
import { projectSnippedView } from './snipProjection.js'

const SNIP_ENABLE_ENV = 'CLAUDE_CODE_ENABLE_HISTORY_SNIP'
const MIN_MESSAGES_TO_SNIP = 60
const KEEP_TAIL_MESSAGES = 40
const SNIP_TRIGGER_ESTIMATED_TOKENS = 12_000
const SNIP_NUDGE_ESTIMATED_TOKENS = 10_000
const SNIP_NUDGE_COOLDOWN_MESSAGES = 12

export const SNIP_NUDGE_TEXT =
  'Your active context is getting large. Consider summarizing or closing older threads to keep focus and response speed high.'

export type SnipCompactResult = {
  messages: Message[]
  executed: boolean
  tokensFreed: number
  boundaryMessage?: Message
}

function hasUuid(message: Message): message is Message & { uuid: string } {
  const uuid = (message as { uuid?: unknown }).uuid
  return typeof uuid === 'string' && uuid.length > 0
}

function isUserOrAssistantMessage(message: Message): boolean {
  const type = (message as { type?: unknown }).type
  return type === 'user' || type === 'assistant'
}

function isCompactBoundary(message: Message): boolean {
  return (
    (message as { type?: unknown }).type === 'system' &&
    (message as { subtype?: unknown }).subtype === 'compact_boundary'
  )
}

function isSnipBoundary(message: Message): boolean {
  return (
    (message as { type?: unknown }).type === 'system' &&
    (message as { subtype?: unknown }).subtype === 'snip_boundary'
  )
}

function toJsonLength(value: unknown): number {
  if (value === null || value === undefined) return 0
  if (typeof value === 'string') return value.length
  try {
    return JSON.stringify(value).length
  } catch {
    return 0
  }
}

function estimateTokens(messages: readonly Message[]): number {
  let chars = 0
  for (const message of messages) {
    chars += toJsonLength(message)
  }
  return Math.ceil(chars / 4)
}

function recentMessagesContainSnipBoundary(messages: readonly Message[]): boolean {
  const start = Math.max(0, messages.length - SNIP_NUDGE_COOLDOWN_MESSAGES)
  for (let i = start; i < messages.length; i++) {
    if (isSnipBoundary(messages[i]!)) return true
  }
  return false
}

function createBoundaryMessage(
  removedUuids: string[],
  tokensFreed: number,
): Message {
  const now = new Date().toISOString()
  return {
    type: 'system',
    subtype: 'snip_boundary',
    level: 'info',
    content: `Context geoptimaliseerd: ${removedUuids.length} berichten gecomprimeerd (~${tokensFreed} tokens vrijgemaakt).`,
    timestamp: now,
    uuid: randomUUID(),
    snipMetadata: {
      removedUuids,
      removedCount: removedUuids.length,
      estimatedTokensFreed: tokensFreed,
    },
  } as Message
}

export function isSnipRuntimeEnabled(): boolean {
  if (process.env.USER_TYPE !== 'ant') return false
  return isEnvTruthy(process.env[SNIP_ENABLE_ENV])
}

export function isSnipMarkerMessage(message: Message): boolean {
  return (
    (message as { type?: unknown }).type === 'system' &&
    (message as { subtype?: unknown }).subtype === 'snip_marker'
  )
}

export function shouldNudgeForSnips(messages: Message[]): boolean {
  if (!isSnipRuntimeEnabled()) return false
  if (messages.length < MIN_MESSAGES_TO_SNIP) return false
  if (recentMessagesContainSnipBoundary(messages)) return false
  return estimateTokens(messages) >= SNIP_NUDGE_ESTIMATED_TOKENS
}

export function snipCompactIfNeeded(
  messages: Message[],
  options?: { force?: boolean },
): SnipCompactResult {
  const force = Boolean(options?.force)
  const projected = projectSnippedView(messages)

  // Force mode is used for replay paths where we must apply already-recorded
  // removals from prior snip boundaries, even if no fresh snip is needed.
  if (force && projected.length !== messages.length) {
    return {
      messages: projected,
      executed: true,
      tokensFreed: 0,
    }
  }

  if (!isSnipRuntimeEnabled()) {
    return { messages: projected, executed: false, tokensFreed: 0 }
  }

  if (
    !force &&
    (projected.length < MIN_MESSAGES_TO_SNIP ||
      estimateTokens(projected) < SNIP_TRIGGER_ESTIMATED_TOKENS)
  ) {
    return { messages: projected, executed: false, tokensFreed: 0 }
  }

  const keepHead =
    projected.length > 0 && (projected[0] as { type?: unknown }).type === 'system'
      ? 1
      : 0
  const tailStart = Math.max(keepHead, projected.length - KEEP_TAIL_MESSAGES)

  const removable: Array<Message & { uuid: string }> = []
  for (let i = keepHead; i < tailStart; i++) {
    const message = projected[i]!
    if (!hasUuid(message)) continue
    if (!isUserOrAssistantMessage(message)) continue
    if (isCompactBoundary(message) || isSnipBoundary(message)) continue
    removable.push(message)
  }

  if (removable.length === 0) {
    return { messages: projected, executed: false, tokensFreed: 0 }
  }

  const removedUuids = removable.map(message => message.uuid)
  const removedSet = new Set(removedUuids)
  const nextMessages = projected.filter(
    message => !(hasUuid(message) && removedSet.has(message.uuid)),
  )

  if (nextMessages.length === projected.length) {
    return { messages: projected, executed: false, tokensFreed: 0 }
  }

  const tokensFreed = estimateTokens(removable)
  return {
    messages: nextMessages,
    executed: true,
    tokensFreed,
    boundaryMessage: createBoundaryMessage(removedUuids, tokensFreed),
  }
}
