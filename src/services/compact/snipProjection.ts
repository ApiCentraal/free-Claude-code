import type { Message } from '../../types/message.js'

type SnipMetadata = {
  removedUuids?: string[]
}

function getRemovedUuids(message: Message): string[] {
  const metadata = (message as { snipMetadata?: SnipMetadata }).snipMetadata
  if (!metadata || !Array.isArray(metadata.removedUuids)) {
    return []
  }
  return metadata.removedUuids.filter(
    (uuid): uuid is string => typeof uuid === 'string' && uuid.length > 0,
  )
}

function getUuid(message: Message): string | undefined {
  const uuid = (message as { uuid?: unknown }).uuid
  return typeof uuid === 'string' && uuid.length > 0 ? uuid : undefined
}

function isSnipMarkerMessageInternal(message: Message): boolean {
  return (
    (message as { type?: unknown }).type === 'system' &&
    (message as { subtype?: unknown }).subtype === 'snip_marker'
  )
}

function hasSnipMetadata(message: Message): boolean {
  return getRemovedUuids(message).length > 0
}

/**
 * UI helper: only true for explicit snip-boundary messages.
 */
export function isSnipBoundaryMessage(message: Message): boolean {
  return (
    (message as { type?: unknown }).type === 'system' &&
    (message as { subtype?: unknown }).subtype === 'snip_boundary' &&
    hasSnipMetadata(message)
  )
}

/**
 * Produces a "runtime context view" where snipped message UUIDs are removed.
 * Boundaries are preserved so replay/resume logic remains deterministic.
 */
export function projectSnippedView(messages: Message[]): Message[] {
  if (messages.length === 0) return messages

  const removed = new Set<string>()
  for (const message of messages) {
    for (const uuid of getRemovedUuids(message)) {
      removed.add(uuid)
    }
  }

  if (removed.size === 0) {
    return messages.filter(message => !isSnipMarkerMessageInternal(message))
  }

  return messages.filter(message => {
    if (isSnipMarkerMessageInternal(message)) return false
    const uuid = getUuid(message)
    return !(uuid && removed.has(uuid))
  })
}

