/**
 * SDK control-plane transport contracts.
 * Recovery-safe shape definitions used by bridge/CLI layers.
 */

export interface SDKControlRequest {
  type: string
  [key: string]: unknown
}

export interface SDKControlResponse {
  type: string
  [key: string]: unknown
}

export interface SDKControlPermissionRequest {
  type: string
  [key: string]: unknown
}

export interface StdinMessage {
  type: string
  [key: string]: unknown
}

export interface StdoutMessage {
  type: string
  [key: string]: unknown
}

export interface SDKPartialAssistantMessage {
  type: string
  [key: string]: unknown
}

