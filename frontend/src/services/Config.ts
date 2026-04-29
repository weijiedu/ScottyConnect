const PRODUCTION_API_URL = 'https://scottyconnect.onrender.com'

/**
 * Resolve API base URL by environment:
 * - local/dev: empty string (same origin + Vite proxy)
 * - production: fixed Render backend URL.
 */
export function getApiBaseUrl(): string {
  // Check if we are in development mode
  if (import.meta.env.DEV) {
    return ''
  }
  return PRODUCTION_API_URL
}

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${getApiBaseUrl()}${normalizedPath}`
}
