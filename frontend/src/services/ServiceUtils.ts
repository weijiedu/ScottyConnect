import StorageUtil from '../common/StorageUtil'

export function authHeaders(): Record<string, string> {
  const token = StorageUtil.getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

function toCamelKey(key: string): string {
  return key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase())
}

export function snakeToCamel<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => snakeToCamel(item)) as T
  }

  if (value !== null && typeof value === 'object' && value.constructor === Object) {
    const result: Record<string, unknown> = {}
    for (const [key, rawValue] of Object.entries(value)) {
      result[toCamelKey(key)] = snakeToCamel(rawValue)
    }
    return result as T
  }

  return value
}
