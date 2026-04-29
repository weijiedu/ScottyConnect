import { useCallback, useEffect, useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import FeedbackStats from './FeedbackStatsPage'
import {
  listMyEvents,
  apiEventToStored,
  deleteEventApi,
  transitionEventApi,
  deleteEventTags,
  getEventTags,
} from '../services/LifecycleService'
import { getRegisteredEvents, unregisterEvent } from '../services/AttendanceService'
import { apiUrl } from '../services/Config'
import type { StoredEvent } from '../types/event'
import StorageUtil from '../common/StorageUtil'
import EventTagDisplay from '../components/EventTagDisplay'
import '../styles/MyEvents.css'

type Tab = 'created' | 'registered'

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  draft: { label: 'Draft', className: 'me-status-draft' },
  published: { label: 'Published', className: 'me-status-published' },
  ended: { label: 'Ended', className: 'me-status-ended' },
  cancelled: { label: 'Cancelled', className: 'me-status-cancelled' },
}

const FALLBACK_STATUS = { label: 'Unknown', className: 'me-status-draft' }

function formatDate(ev: StoredEvent): string {
  const d = new Date(ev.date + 'T00:00:00')
  const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  if (ev.startTime) {
    const [h, m] = ev.startTime.split(':')
    const hour = parseInt(h, 10)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    const h12 = hour % 12 || 12
    return `${dateStr} · ${h12}:${m} ${ampm}`
  }
  return dateStr
}

function getActions(ev: StoredEvent): { label: string; className: string; action: string }[] {
  switch (ev.status) {
    case 'draft':
      return [
        { label: 'Tasks', className: 'me-action-publish', action: 'tasks' },
        { label: 'Edit', className: 'me-action-secondary', action: 'edit' },
        { label: 'Delete', className: 'me-action-danger', action: 'delete' },
      ]
    case 'published':
      return [
        { label: 'Tasks', className: 'me-action-publish', action: 'tasks' },
        { label: 'End Event', className: 'me-action-secondary', action: 'end' },
        { label: 'Cancel', className: 'me-action-danger', action: 'cancel' },
      ]
    case 'ended':
      return [
        { label: 'Tasks', className: 'me-action-secondary', action: 'tasks' },
        { label: 'View Feedback', className: 'me-action-publish', action: 'feedback' },
      ]
    case 'cancelled':
      return [
        { label: 'Tasks', className: 'me-action-secondary', action: 'tasks' },
      ]
    default:
      return []
  }
}

export default function MyEventsPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('created')
  const [deleteTarget, setDeleteTarget] = useState<StoredEvent | null>(null)
  const [feedbackTarget, setFeedbackTarget] = useState<StoredEvent | null>(null)
  const [createdEvents, setCreatedEvents] = useState<StoredEvent[]>([])
  const [createdLoading, setCreatedLoading] = useState(true)
  const [createdError, setCreatedError] = useState('')
  const [registeredEvents, setRegisteredEvents] = useState<StoredEvent[]>([])
  const [registeredLoading, setRegisteredLoading] = useState(true)
  const [registeredError, setRegisteredError] = useState('')
  const [actionError, setActionError] = useState('')
  const [tagsByEventId, setTagsByEventId] = useState<Record<string, string[]>>({})
  const [avgRatingByEventId, setAvgRatingByEventId] = useState<Record<string, string>>({})
  const fetchedRatingsRef = useRef<Set<string>>(new Set())

  const refreshCreated = useCallback(async () => {
    if (!StorageUtil.getToken()) {
      setCreatedEvents([])
      setCreatedError('Sign in to see events you created.')
      setCreatedLoading(false)
      return
    }
    setCreatedLoading(true)
    try {
      const list = await listMyEvents()
      setCreatedEvents(list.map(apiEventToStored))
      setCreatedError('')
    } catch (e) {
      setCreatedError(e instanceof Error ? e.message : 'Failed to load events')
      setCreatedEvents([])
    } finally {
      setCreatedLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshCreated()
  }, [refreshCreated])

  // Fetch average rating for each ended registered event (once per event id)
  useEffect(() => {
    const token = StorageUtil.getToken()
    if (!token) return
    const endedEvents = registeredEvents.filter((ev) => ev.status === 'ended')
    const toFetch = endedEvents.filter((ev) => !fetchedRatingsRef.current.has(ev.id))
    if (toFetch.length === 0) return

    toFetch.forEach((ev) => fetchedRatingsRef.current.add(ev.id))

    toFetch.forEach(async (ev) => {
      try {
        const res = await fetch(apiUrl(`/api/feedback/events/${ev.id}`), {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (res.ok && data.feedbacks?.length > 0) {
          const avg = (
            data.feedbacks.reduce((sum: number, f: { rating: number }) => sum + f.rating, 0) /
            data.feedbacks.length
          ).toFixed(1)
          setAvgRatingByEventId((prev) => ({ ...prev, [ev.id]: avg }))
        }
      } catch {
        // silently ignore — rating is best-effort
      }
    })
  }, [registeredEvents])

  useEffect(() => {
    if (!StorageUtil.getToken()) {
      setRegisteredEvents([])
      setRegisteredError('Sign in to see events you registered for.')
      setRegisteredLoading(false)
      return
    }

    let cancelled = false
    ;(async () => {
      setRegisteredLoading(true)
      try {
        const list = await getRegisteredEvents()
        if (!cancelled) {
          setRegisteredEvents(list.map(apiEventToStored))
          setRegisteredError('')
        }
      } catch (e) {
        if (!cancelled) {
          setRegisteredError(e instanceof Error ? e.message : 'Failed to load events')
          setRegisteredEvents([])
        }
      } finally {
        if (!cancelled) setRegisteredLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  // Fetch event tags for all displayed events (created + registered), in parallel.
  useEffect(() => {
    const allEvents = [...createdEvents, ...registeredEvents]
    if (allEvents.length === 0) {
      setTagsByEventId({})
      return
    }
    let cancelled = false
    ;(async () => {
      const results = await Promise.all(
        allEvents.map((ev) =>
          getEventTags(ev.id)
            .then((ids) => [ev.id, ids] as [string, string[]])
            .catch(() => [ev.id, [] as string[]] as [string, string[]]),
        ),
      )
      if (cancelled) return
      const map: Record<string, string[]> = {}
      for (const [id, ids] of results) map[id] = ids
      setTagsByEventId(map)
    })()
    return () => {
      cancelled = true
    }
  }, [createdEvents, registeredEvents])

  async function handleAction(ev: StoredEvent, action: string) {
    if (action === 'tasks') {
      navigate(`/events/${ev.id}/tasks`)
      return
    }
    if (action === 'edit') {
      navigate(`/events/${ev.id}/edit`)
      return
    }
    if (action === 'delete') {
      setDeleteTarget(ev)
      return
    }
    if (action === 'feedback') {
      setFeedbackTarget(ev)
      return
    }
    if (action === 'rate') {
      navigate(`/events/${ev.id}/feedback`, {
        state: {
          title: ev.title,
          date: ev.date,
          startTime: ev.startTime,
          endTime: ev.endTime,
        },
      })
      return
    }
    if (action === 'end') {
      setActionError('')
      try {
        await transitionEventApi(ev.id, 'ended')
        await refreshCreated()
      } catch (e) {
        setActionError(e instanceof Error ? e.message : 'Failed to update event')
      }
      return
    }
    if (action === 'cancel') {
      setActionError('')
      try {
        await transitionEventApi(ev.id, 'cancelled')
        await refreshCreated()
      } catch (e) {
        setActionError(e instanceof Error ? e.message : 'Failed to update event')
      }
      return
    }
    if (action === 'unregister') {
      setActionError('')
      try {
        await unregisterEvent(ev.id)
        const list = await getRegisteredEvents()
        setRegisteredEvents(list.map(apiEventToStored))
        setRegisteredError('')
      } catch (e) {
        setActionError(e instanceof Error ? e.message : 'Failed to unregister')
      }
      return
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return
    setActionError('')
    try {
      // Delete event tags first (best-effort — don't block deletion if it fails)
      try {
        await deleteEventTags(deleteTarget.id)
      } catch (tagErr) {
        console.error('Failed to delete event tags:', tagErr)
      }
      await deleteEventApi(deleteTarget.id)
      setDeleteTarget(null)
      await refreshCreated()
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to delete')
    }
  }

  function openEventDetails(eventId: string) {
    navigate(`/events/${eventId}`)
  }

  return (
    <div className="me-page">
      <header className="me-header">
        <div className="me-header-inner">
          <Link to="/mainpage" className="me-back">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Back to home
          </Link>
        </div>
      </header>

      <main className="me-content">
        {actionError && (
          <div className="me-inline-error" role="alert">
            {actionError}
          </div>
        )}
        <h1 className="me-title">My Events</h1>
        <p className="me-subtitle">Events you've created or registered for.</p>

        <div className="me-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={tab === 'created'}
            className={`me-tab ${tab === 'created' ? 'me-tab-active' : ''}`}
            onClick={() => {
              setActionError('')
              setTab('created')
            }}
          >
            Created ({createdEvents.length})
          </button>
          <button
            role="tab"
            aria-selected={tab === 'registered'}
            className={`me-tab ${tab === 'registered' ? 'me-tab-active' : ''}`}
            onClick={() => {
              setActionError('')
              setTab('registered')
            }}
          >
            Registered ({registeredEvents.length})
          </button>
        </div>

        {tab === 'created' && (
          <section className="me-section" aria-label="Created events">
            {createdLoading && <p className="me-empty">Loading…</p>}
            {!createdLoading && createdError && (
              <div className="me-empty">
                <p>{createdError}</p>
              </div>
            )}
            {!createdLoading && !createdError && createdEvents.length === 0 && (
              <div className="me-empty">
                <p>You haven't created any events yet.</p>
                <Link to="/publish-event" className="me-empty-link">Create your first event</Link>
              </div>
            )}
            {!createdLoading && !createdError && createdEvents.length > 0 && (
              <ul className="me-event-list">
                {createdEvents.map((ev) => {
                  const sc = STATUS_CONFIG[ev.status] ?? FALLBACK_STATUS
                  const actions = getActions(ev)
                  return (
                    <li key={ev.id}>
                      <article
                        className="me-event-card"
                        onClick={() => openEventDetails(ev.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            openEventDetails(ev.id)
                          }
                        }}
                        role="button"
                        tabIndex={0}
                      >
                        <div className="me-event-top">
                          <div className="me-event-body">
                            <h3 className="me-event-title">{ev.title}</h3>
                            <p className="me-event-meta">{formatDate(ev)}</p>
                            {ev.location && <p className="me-event-meta">{ev.location}</p>}
                            {tagsByEventId[ev.id] && tagsByEventId[ev.id].length > 0 && (
                              <EventTagDisplay tagIds={tagsByEventId[ev.id]} limit={3} />
                            )}
                          </div>
                          <span className={`me-status-badge ${sc.className}`}>{sc.label}</span>
                        </div>
                        {actions.length > 0 && (
                          <div className="me-event-actions">
                            {actions.map((a) => (
                              <button
                                key={a.action}
                                className={`me-action-btn ${a.className}`}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  void handleAction(ev, a.action)
                                }}
                              >
                                {a.label}
                              </button>
                            ))}
                          </div>
                        )}
                      </article>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
        )}

        {tab === 'registered' && (
          <section className="me-section" aria-label="Registered events">
            {registeredLoading && <p className="me-empty">Loading…</p>}
            {!registeredLoading && registeredError && (
              <div className="me-empty">
                <p>{registeredError}</p>
              </div>
            )}
            {!registeredLoading && !registeredError && registeredEvents.length === 0 && (
              <div className="me-empty">
                <p>You haven't registered for any events yet.</p>
                <Link to="/mainpage" className="me-empty-link">Browse active events</Link>
              </div>
            )}
            {!registeredLoading && !registeredError && registeredEvents.length > 0 && (
              <ul className="me-event-list">
                {registeredEvents.map((ev) => {
                  const sc = STATUS_CONFIG[ev.status] ?? FALLBACK_STATUS
                  return (
                    <li key={ev.id}>
                      <article
                        className="me-event-card"
                        onClick={() => openEventDetails(ev.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            openEventDetails(ev.id)
                          }
                        }}
                        role="button"
                        tabIndex={0}
                      >
                        <div className="me-event-top">
                          <div className="me-event-body">
                            <h3 className="me-event-title">{ev.title}</h3>
                            <p className="me-event-meta">{formatDate(ev)}</p>
                            {ev.location && <p className="me-event-meta">{ev.location}</p>}
                            {ev.status === 'ended' && avgRatingByEventId[ev.id] && (
                              <p className="me-event-meta">Rating: {avgRatingByEventId[ev.id]} / 5.0</p>
                            )}
                            {tagsByEventId[ev.id] && tagsByEventId[ev.id].length > 0 && (
                              <EventTagDisplay tagIds={tagsByEventId[ev.id]} limit={3} />
                            )}
                          </div>
                          <span className={`me-status-badge ${sc.className}`}>{sc.label}</span>
                        </div>
                        {(ev.status === 'published' || ev.status === 'ended' || ev.status === 'cancelled') && (
                          <div className="me-event-actions">
                            <button
                              className="me-action-btn me-action-publish"
                              onClick={(e) => {
                                e.stopPropagation()
                                void handleAction(ev, 'tasks')
                              }}
                            >
                              Tasks
                            </button>
                            {ev.status === 'ended' && (
                              <button
                                className="me-action-btn me-action-publish"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  navigate(`/events/${ev.id}/feedback`, {
                                    state: {
                                      title: ev.title,
                                      date: ev.date,
                                      startTime: ev.startTime,
                                      endTime: ev.endTime,
                                    },
                                  })
                                }}
                              >
                                Rate This Event
                              </button>
                            )}
                            {ev.status === 'published' && (
                              <button
                                className="me-action-btn me-action-danger"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  void handleAction(ev, 'unregister')
                                }}
                              >
                                Cancel Registration
                              </button>
                            )}
                          </div>
                        )}
                      </article>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
        )}
      </main>

      <footer className="me-footer">
        <p>ScottyConnect · Carnegie Mellon University</p>
      </footer>

      {feedbackTarget && (
        <FeedbackStats
          event={feedbackTarget}
          onClose={() => setFeedbackTarget(null)}
        />
      )}

      {deleteTarget && (
        <div className="me-modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="me-modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="me-modal-title">Delete Draft?</h2>
            <p className="me-modal-message">
              Are you sure you want to delete "{deleteTarget.title}"? This action cannot be undone.
            </p>
            <div className="me-modal-actions">
              <button className="me-modal-btn me-modal-btn-danger" onClick={confirmDelete}>
                Delete
              </button>
              <button className="me-modal-btn me-modal-btn-secondary" onClick={() => setDeleteTarget(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
