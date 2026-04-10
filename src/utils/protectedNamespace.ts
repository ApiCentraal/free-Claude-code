/**
 * Conservative protected-namespace detector for internal COO/k8s environments.
 * If signals are ambiguous, we return true to avoid under-reporting risk.
 */

const OPEN_NAMESPACE_ALLOWLIST = new Set([
  'default',
  'homespace',
  'home',
  'dev',
  'development',
  'sandbox',
  'local',
  'test',
])

function normalize(value: string | undefined): string {
  return (value ?? '').trim().toLowerCase()
}

export function checkProtectedNamespace(): boolean {
  const namespace = normalize(
    process.env.COO_NAMESPACE ??
      process.env.KUBERNETES_NAMESPACE ??
      process.env.POD_NAMESPACE,
  )

  // No namespace signal usually means local laptop/dev shell.
  if (!namespace) {
    return false
  }

  if (OPEN_NAMESPACE_ALLOWLIST.has(namespace)) {
    return false
  }

  if (namespace.startsWith('home-') || namespace.startsWith('hs-')) {
    return false
  }

  // Any explicit privileged/sensitive markers are protected.
  if (
    namespace.includes('priv') ||
    namespace.includes('secure') ||
    namespace.includes('protected') ||
    namespace.includes('asl3') ||
    namespace.includes('prod')
  ) {
    return true
  }

  // Conservative fallback.
  return true
}

