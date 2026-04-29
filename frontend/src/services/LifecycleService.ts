import { authHeaders } from './ServiceUtils'
import { apiUrl } from './Config'
import { apiEventFromSnake, type PublicEvent } from '../schemas/event'
import type { StoredEvent } from '../types/event'


function clientTzQueryParam(): string {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    if (tz) return `client_tz=${encodeURIComponent(tz)}`
  } catch {
    /* ignore */
  }
  return ''
}

export function getLifecycleClockSearch(): string {
  const p = clientTzQueryParam()
  return p ? `?${p}` : ''
}

interface APIEventResponse {
  message: string
  event: Record<string, unknown> | null
  code: number
}

interface APIEventListResponse {
  message: string
  events: Record<string, unknown>[]
  code: number
}

interface APISyncExpiredResponse {
  scanned: number
  ended: number
}

export type { PublicEvent } from '../schemas/event'

export function apiEventToStored(ev: PublicEvent): StoredEvent {
  return {
    id: ev.id,
    title: ev.title,
    description: ev.description,
    date: ev.date ?? '',
    startTime: ev.startTime ?? '',
    endTime: ev.endTime ?? '',
    location: ev.location ?? '',
    capacity: ev.capacity,
    registeredCount: ev.registeredCount ?? 0,
    status: ev.status,
    ownerId: ev.ownerId,
    createdAt: ev.createdAt,
  }
}

export async function createEvent(
  form: {
    title: string
    description: string
    date: string
    startTime: string
    endTime: string
    location: string
    capacity: string
  },
  status: 'draft' | 'published',
): Promise<PublicEvent> {
  const res = await fetch(apiUrl('/api/lifecycle/events'), {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({
      title: form.title.trim(),
      description: form.description.trim(),
      date: form.date,
      start_time: form.startTime,
      end_time: form.endTime,
      location: form.location.trim(),
      capacity: form.capacity ? parseInt(form.capacity, 10) : null,
      status,
    }),
  })

  const data: APIEventResponse = await res.json()
  if (!res.ok || !data.event) {
    throw new Error(data.message || 'Failed to create event')
  }
  return apiEventFromSnake(data.event)
}

export async function getEvent(eventId: string): Promise<PublicEvent> {
  const path = `/api/lifecycle/events/${encodeURIComponent(eventId)}${getLifecycleClockSearch()}`
  const res = await fetch(apiUrl(path), {
    headers: authHeaders(),
  })
  const data: APIEventResponse = await res.json()
  if (!res.ok || !data.event) {
    throw new Error(data.message || 'Event not found')
  }
  return apiEventFromSnake(data.event)
}

export async function listMyEvents(): Promise<PublicEvent[]> {
  const path = `/api/lifecycle/events/mine${getLifecycleClockSearch()}`
  const res = await fetch(apiUrl(path), {
    headers: authHeaders(),
  })
  const data: APIEventListResponse = await res.json()
  if (!res.ok) {
    throw new Error(data.message || 'Failed to load your events')
  }
  return data.events.map((e) => apiEventFromSnake(e))
}

export async function listPublishedEvents(): Promise<PublicEvent[]> {
  const path = `/api/lifecycle/events/published${getLifecycleClockSearch()}`
  const res = await fetch(apiUrl(path))
  const data: APIEventListResponse = await res.json()
  if (!res.ok) {
    throw new Error(data.message || 'Failed to load events')
  }
  return data.events.map((e) => apiEventFromSnake(e))
}

export async function syncExpiredPublishedEvents(): Promise<{ scanned: number; ended: number }> {
  const path = `/api/lifecycle/events/sync-expired${getLifecycleClockSearch()}`
  const res = await fetch(apiUrl(path), { method: 'POST' })
  const data: APISyncExpiredResponse = await res.json()
  if (!res.ok) {
    throw new Error('Failed to sync expired events')
  }
  return { scanned: data.scanned ?? 0, ended: data.ended ?? 0 }
}

export async function updateEvent(
  eventId: string,
  form: {
    title: string
    description: string
    date: string
    startTime: string
    endTime: string
    location: string
    capacity: string
  },
  status: 'draft' | 'published',
): Promise<PublicEvent> {
  const res = await fetch(apiUrl(`/api/lifecycle/events/${encodeURIComponent(eventId)}`), {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({
      title: form.title.trim(),
      description: form.description.trim(),
      date: form.date,
      start_time: form.startTime,
      end_time: form.endTime,
      location: form.location.trim(),
      capacity: form.capacity ? parseInt(form.capacity, 10) : null,
      status,
    }),
  })
  const data: APIEventResponse = await res.json()
  if (!res.ok || !data.event) {
    throw new Error(data.message || 'Failed to update event')
  }
  return apiEventFromSnake(data.event)
}

export async function deleteEventApi(eventId: string): Promise<void> {
  const res = await fetch(apiUrl(`/api/lifecycle/events/${encodeURIComponent(eventId)}`), {
    method: 'DELETE',
    headers: authHeaders(),
  })
  const data: APIEventResponse = await res.json()
  if (!res.ok) {
    throw new Error(data.message || 'Failed to delete event')
  }
}

export async function transitionEventApi(
  eventId: string,
  targetStatus: string,
): Promise<PublicEvent> {
  const res = await fetch(apiUrl(`/api/lifecycle/events/${encodeURIComponent(eventId)}/transition`), {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ target_status: targetStatus }),
  })
  const data: APIEventResponse = await res.json()
  if (!res.ok || !data.event) {
    throw new Error(data.message || 'Failed to update event status')
  }
  return apiEventFromSnake(data.event)
}

// ---- Event Tags ----

interface APIEventTagsResponse {
  message: string
  event_id: string
  tag_ids: string[]
  code: number
}

export async function getEventTags(eventId: string): Promise<string[]> {
  const url = apiUrl(`/api/recommendation/event-tags/${encodeURIComponent(eventId)}`)
  const res = await fetch(url, { headers: authHeaders() })
  if (!res.ok) {
    throw new Error(`Failed to load event tags: ${res.status} ${res.statusText}`)
  }
  const data: APIEventTagsResponse = await res.json()
  return data.tag_ids
}

export async function setEventTags(eventId: string, tagIds: string[]): Promise<string[]> {
  const url = apiUrl(`/api/recommendation/event-tags/${encodeURIComponent(eventId)}`)
  const res = await fetch(url, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ tag_ids: tagIds }),
  })
  if (!res.ok) {
    throw new Error(`Failed to save event tags: ${res.status} ${res.statusText}`)
  }
  const data: APIEventTagsResponse = await res.json()
  return data.tag_ids
}

export async function deleteEventTags(eventId: string): Promise<void> {
  const url = apiUrl(`/api/recommendation/event-tags/${encodeURIComponent(eventId)}`)
  const res = await fetch(url, { method: 'DELETE', headers: authHeaders() })
  if (!res.ok) {
    throw new Error(`Failed to delete event tags: ${res.status} ${res.statusText}`)
  }
}
