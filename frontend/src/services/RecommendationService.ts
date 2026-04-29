import { type RecommendationStrategy } from '../common/StorageUtil'
import { authHeaders } from './ServiceUtils'
import { apiUrl } from './Config'
import { apiEventFromSnake, type PublicEvent } from '../schemas/event'

interface APIRecommendationResponse {
  message: string
  strategy: string
  events: Record<string, unknown>[]
  code: number
}

interface APIPreferenceResponse {
  message: string
  user_id: string
  preferred_strategy: string
  code: number
}

/** Fetch ranked, published event recommendations for a user. */
export async function getRecommendations(
  userId: string,
  strategy: RecommendationStrategy,
): Promise<PublicEvent[]> {
  const url = apiUrl(`/api/recommendation/${encodeURIComponent(userId)}?strategy=${encodeURIComponent(strategy)}`)
  const res = await fetch(url, { headers: authHeaders() })
  const data: APIRecommendationResponse = await res.json()
  if (!res.ok) {
    throw new Error(data.message || 'Failed to load recommendations')
  }
  return data.events.map((e) => apiEventFromSnake(e))
}

const VALID_STRATEGIES: RecommendationStrategy[] = ['tag', 'popularity', 'hybrid']

function coerceStrategy(raw: string): RecommendationStrategy {
  return (VALID_STRATEGIES as string[]).includes(raw)
    ? (raw as RecommendationStrategy)
    : 'hybrid'
}

/** Fetch the user's saved recommendation strategy preference. */
export async function getUserPreference(userId: string): Promise<RecommendationStrategy> {
  const url = apiUrl(`/api/recommendation/preferences/${encodeURIComponent(userId)}`)
  const res = await fetch(url, { headers: authHeaders() })
  if (!res.ok) {
    throw new Error(`Failed to load preference: ${res.status} ${res.statusText}`)
  }
  const data: APIPreferenceResponse = await res.json()
  return coerceStrategy(data.preferred_strategy)
}

/** Save the user's preferred recommendation strategy. */
export async function setUserPreference(
  userId: string,
  strategy: RecommendationStrategy,
): Promise<RecommendationStrategy> {
  const url = apiUrl(`/api/recommendation/preferences/${encodeURIComponent(userId)}`)
  const res = await fetch(url, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ preferred_strategy: strategy }),
  })
  if (!res.ok) {
    throw new Error(`Failed to save preference: ${res.status} ${res.statusText}`)
  }
  const data: APIPreferenceResponse = await res.json()
  return coerceStrategy(data.preferred_strategy)
}

// ---- Tags ------------------------------------------------------------------

export interface Tag {
  id: string
  slug: string
  displayName: string | null
}

interface APITagListResponse {
  message: string
  tags: Array<{ id: string; slug: string; display_name: string | null }>
  code: number
}

interface APIUserTagsResponse {
  message: string
  user_id: string
  tag_ids: string[]
  code: number
}

/** Fetch every selectable tag. */
export async function getAllTags(): Promise<Tag[]> {
  const res = await fetch(apiUrl('/api/recommendation/tags'), { headers: authHeaders() })
  if (!res.ok) {
    throw new Error(`Failed to load tags: ${res.status} ${res.statusText}`)
  }
  const data: APITagListResponse = await res.json()
  return data.tags.map((t) => ({
    id: t.id,
    slug: t.slug,
    displayName: t.display_name,
  }))
}

/** Fetch the tag_ids the user is currently interested in. */
export async function getUserTags(userId: string): Promise<string[]> {
  const url = apiUrl(`/api/recommendation/user-tags/${encodeURIComponent(userId)}`)
  const res = await fetch(url, { headers: authHeaders() })
  if (!res.ok) {
    throw new Error(`Failed to load user tags: ${res.status} ${res.statusText}`)
  }
  const data: APIUserTagsResponse = await res.json()
  return data.tag_ids
}

/** Replace the user's interested-tag set with the provided list. */
export async function setUserTags(userId: string, tagIds: string[]): Promise<string[]> {
  const url = apiUrl(`/api/recommendation/user-tags/${encodeURIComponent(userId)}`)
  const res = await fetch(url, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ tag_ids: tagIds }),
  })
  if (!res.ok) {
    throw new Error(`Failed to save user tags: ${res.status} ${res.statusText}`)
  }
  const data: APIUserTagsResponse = await res.json()
  return data.tag_ids
}
