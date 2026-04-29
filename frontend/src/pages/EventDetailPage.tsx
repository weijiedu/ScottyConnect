import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import StorageUtil from '../common/StorageUtil'
import { apiUrl } from '../services/Config'
import { getEvent, apiEventToStored, getEventTags } from '../services/LifecycleService'
import {
  getRegistrationStatus,
  registerEvent,
  unregisterEvent,
  getRegisteredUsers,
} from '../services/AttendanceService'
import EventTagDisplay from '../components/EventTagDisplay'
import type { StoredEvent } from '../types/event'
import '../styles/EventDetail.css'
import { authHeaders } from '../services/ServiceUtils'

interface TaskPreview {
  id: string
  parent_id: string | null
  title: string
  children: TaskPreview[]
}

function flattenTasks(nodes: TaskPreview[], depth = 0): { task: TaskPreview; depth: number }[] {
  const result: { task: TaskPreview; depth: number }[] = []
  for (const node of nodes) {
    result.push({ task: node, depth })
    if (node.children?.length) {
      result.push(...flattenTasks(node.children, depth + 1))
    }
  }
  return result
}

// Labels for the event status
const STATUS_LABELS: Record<StoredEvent['status'], string> = {
  draft: 'Draft',
  published: 'Published',
  ended: 'Ended',
  cancelled: 'Cancelled',
}

// Format the date and time of the event
function formatDateTime(ev: StoredEvent): string {
  const d = new Date(ev.date + 'T00:00:00')
  const dateLabel = d.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })

  if (!ev.startTime) return dateLabel

  const [startH, startM] = ev.startTime.split(':')
  const startHour = parseInt(startH, 10)
  const startAmpm = startHour >= 12 ? 'PM' : 'AM'
  const start12 = startHour % 12 || 12
  let timeLabel = `${start12}:${startM} ${startAmpm}`

  if (ev.endTime) {
    const [endH, endM] = ev.endTime.split(':')
    const endHour = parseInt(endH, 10)
    const endAmpm = endHour >= 12 ? 'PM' : 'AM'
    const end12 = endHour % 12 || 12
    timeLabel += ` - ${end12}:${endM} ${endAmpm}`
  }

  return `${dateLabel} · ${timeLabel}`
}

// Format the capacity of the event
function formatCapacity(ev: StoredEvent): string {
  if (ev.status != "published") return 'Closed'
  if (ev.capacity == null) return 'Open registration'
  if (ev.registeredCount == null) return 'Open registration'
  return `${ev.capacity - ev.registeredCount} / ${ev.capacity} spots remaining`
}

export default function EventDetailPage() {
  // Get the event ID from the URL
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  // Current user
  const currentUser = StorageUtil.getUser()
  const currentUserId = currentUser?.id ?? ''
  
  // State variables
  const [event, setEvent] = useState<StoredEvent | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [isRegistered, setIsRegistered] = useState(false)
  const [registrationLoading, setRegistrationLoading] = useState(true)
  const [registrationError, setRegistrationError] = useState('')
  const [registrationSaving, setRegistrationSaving] = useState(false)
  const [registerSuccessMessage, setRegisterSuccessMessage] = useState('')
  const [hostLabel, setHostLabel] = useState('')
  const [tagIds, setTagIds] = useState<string[]>([])
  const [tasks, setTasks] = useState<TaskPreview[]>([])
  const [tasksLoading, setTasksLoading] = useState(true)

  async function refreshRegisteredCount(eventId: string) {
    const users = await getRegisteredUsers(eventId)
    setEvent((prev) => {
      if (!prev) return prev
      return { ...prev, registeredCount: users.length }
    })
  }

  // Load event details on mount
  useEffect(() => {
    if (!id) return

    let cancelled = false
    ;(async () => {
      try {
        const ev = await getEvent(id)
        const registeredUsers = await getRegisteredUsers(id)
        ev.registeredCount = registeredUsers.length
        if (!cancelled) {
          setEvent(apiEventToStored(ev))
          setLoadError('')
        }
      } catch (e) {
        if (!cancelled) {
          setEvent(null)
          setLoadError(e instanceof Error ? e.message : 'Failed to load event details')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [id])

  // Load registration status on mount
  useEffect(() => {
    if (!id) return

    let cancelled = false
    ;(async () => {
      try {
        const registered = await getRegistrationStatus(id)
        if (!cancelled) {
          setIsRegistered(registered)
          setRegistrationError('')
        }
      } catch (e) {
        if (!cancelled) {
          setRegistrationError(e instanceof Error ? e.message : 'Failed to load registration status')
        }
      } finally {
        if (!cancelled) setRegistrationLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [id])

  // Resolve host display name (username when available via discover cache or API)
  useEffect(() => {
    if (!event) {
      setHostLabel('')
      return
    }

    const me = StorageUtil.getUser()
    if (me?.id === event.ownerId) {
      setHostLabel(me.username ? me.username : 'You')
      return
    }

    setHostLabel('')
    let cancelled = false
    ;(async () => {
      try {
        const raw = sessionStorage.getItem('scotty_networking_discover')
        if (raw) {
          const users = JSON.parse(raw) as { id?: string; username?: string }[]
          const hit = users.find((u) => u.id === event.ownerId)
          if (hit?.username) {
            if (!cancelled) setHostLabel(hit.username)
            return
          }
        }
      } catch {
        /* ignore cache parse errors */
      }

      try {
        const res = await fetch(apiUrl('/api/accounts/discover'))
        const data = (await res.json()) as { users?: { id: string; username: string }[] }
        const hit = data.users?.find((u) => u.id === event.ownerId)
        if (!cancelled) {
          setHostLabel(hit?.username ? hit.username : 'Organizer')
        }
      } catch {
        if (!cancelled) setHostLabel('Organizer')
      }
    })()

    return () => {
      cancelled = true
    }
  }, [event])

  // Load event tags on mount
  useEffect(() => {
    if (!id) {
      setTagIds([])
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const ids = await getEventTags(id)
        if (!cancelled) setTagIds(ids)
      } catch {
        if (!cancelled) setTagIds([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id])

  // Determine if the current user is the event owner or a registered participant
  const isOwner = event !== null && event.ownerId === currentUserId
  const canViewTasks = isOwner || isRegistered

  // Load task list when the user has access
  useEffect(() => {
    if (!id || !event) return
    
    if (!isOwner && registrationLoading) return
    if (!canViewTasks) {
      setTasksLoading(false)
      return
    }

    let cancelled = false
    setTasksLoading(true)
    ;(async () => {
      try {
        const headers: Record<string, string> = {
          ...authHeaders(),
          'X-Event-Owner-Id': event.ownerId,
          'X-Event-Status': event.status,
        }
        const res = await fetch(apiUrl(`/api/tasks/events/${encodeURIComponent(id)}`), { headers })
        const data = await res.json()
        if (!cancelled) {
          setTasks(res.ok ? (data.tasks ?? []) : [])
        }
      } catch {
        if (!cancelled) setTasks([])
      } finally {
        if (!cancelled) setTasksLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [id, event, isOwner, canViewTasks, registrationLoading])

  // Handles the registration click event
  async function handleRegistrationClick() {
    if (!id || registrationSaving) return

    setRegistrationSaving(true)
    setRegistrationError('')
    try {
      if (isRegistered) {
        const registered = await unregisterEvent(id)
        setIsRegistered(registered)
        await refreshRegisteredCount(id)
        setRegisterSuccessMessage('Successfully unregistered from the event.')
      } else {
        const registered = await registerEvent(id)
        setIsRegistered(registered)
        await refreshRegisteredCount(id)
        setRegisterSuccessMessage('Successfully registered for the event.')
      }
    } catch (e) {
      setRegistrationError(e instanceof Error ? e.message : 'Failed to update registration')
    } finally {
      setRegistrationSaving(false)
    }
  }

  // Determine if the event is published
  const isPublished = event?.status === 'published'

  // Determine if the registration button is disabled
  const isRegistrationButtonDisabled =
    !isPublished || registrationLoading || registrationSaving || loading || !!loadError

  // Determine the label for the registration button
  const registrationButtonLabel = isPublished
    ? isRegistered
      ? 'Cancel RSVP'
      : 'RSVP'
    : 'RSVP Unavailable'

  // Render the event detail page
  return (
    <div className="event-detail-page">
      <header className="event-detail-header">
        <div className="event-detail-header-inner">
          <Link to="/mainpage" className="event-detail-back">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Back to home
          </Link>
        </div>
      </header>

      <main className="event-detail-content">
        {loading && <p className="event-detail-muted">Loading event details...</p>}

        {!loading && loadError && (
          <div className="event-detail-alert" role="alert">
            <p>{loadError}</p>
            <Link to="/mainpage" className="event-detail-link">
              Return to home
            </Link>
          </div>
        )}

        {!loading && !loadError && event && (
          <article className="event-detail-shell">
            <section className="event-detail-hero">
              <div className="event-detail-hero-main">
                <div className="event-detail-hero-copy">
                  <h1 className="event-detail-title">{event.title}</h1>

                  <div className="event-detail-hero-highlights" aria-label="Event summary">
                    <div className="event-detail-highlight">
                      <span className="event-detail-highlight-icon" aria-hidden>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                          <rect x="3" y="5" width="18" height="16" rx="2" />
                          <path d="M16 3v4M8 3v4M3 10h18" />
                        </svg>
                      </span>
                      <div className="event-detail-highlight-text">
                        <div className="event-detail-highlight-label">When</div>
                        <div className="event-detail-highlight-value">{formatDateTime(event)}</div>
                      </div>
                    </div>

                    <div className="event-detail-highlight">
                      <span className="event-detail-highlight-icon" aria-hidden>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                          <path d="M12 21s7-4.5 7-11a7 7 0 1 0-14 0c0 6.5 7 11 7 11z" />
                          <circle cx="12" cy="10" r="2.5" />
                        </svg>
                      </span>
                      <div className="event-detail-highlight-text">
                        <div className="event-detail-highlight-label">Where</div>
                        <div className="event-detail-highlight-value">{event.location || 'TBA'}</div>
                      </div>
                    </div>
                  </div>

                  {tagIds.length > 0 && (
                    <div className="event-detail-hero-tags" aria-label="Tags">
                      <EventTagDisplay tagIds={tagIds} limit={tagIds.length} />
                    </div>
                  )}
                </div>

                <aside className="event-detail-hero-action" aria-label="RSVP">
                  <span className={`event-detail-status event-detail-status-${event.status}`}>
                    {STATUS_LABELS[event.status]}
                  </span>
                  <div className="event-detail-actions">
                    <button
                      type="button"
                      className={`event-detail-register-btn ${
                        isRegistered && isPublished ? 'unregister' : ''
                      }`}
                      disabled={isRegistrationButtonDisabled}
                      onClick={handleRegistrationClick}
                    >
                      {registrationSaving ? 'Saving...' : registrationButtonLabel}
                    </button>
                  </div>

                  <div className="event-detail-capacity" aria-label="Registration status">
                    {formatCapacity(event)}
                  </div>
                </aside>
              </div>
            </section>

            {(registerSuccessMessage || registrationError) && (
              <div className="event-detail-feedback" aria-live="polite">
                {registerSuccessMessage && (
                  <div className="event-detail-success-message">{registerSuccessMessage}</div>
                )}
                {registrationError && <p className="event-detail-inline-error">{registrationError}</p>}
              </div>
            )}

            <section className="event-detail-body">
              <div className="event-detail-body-main">
                <h2 className="event-detail-section-title">About</h2>
                <p className="event-detail-description">{event.description}</p>
              </div>

              <div className="event-detail-body-side">
                <h2 className="event-detail-section-title">Organizer</h2>
                <div className="event-detail-details">
                  <div className="event-detail-detail-row event-detail-organizer-row">
                    {hostLabel || '—'}
                  </div>
                </div>
              </div>
            </section>

            <section className="event-detail-tasks-section">
              <div className="event-detail-tasks-header">
                <h2 className="event-detail-section-title">Tasks</h2>
                {canViewTasks && (
                  <button
                    type="button"
                    className="event-detail-tasks-view-btn"
                    onClick={() => navigate(`/events/${id}/tasks`)}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
                      <rect x="9" y="3" width="6" height="4" rx="1" />
                      <path d="M9 12h6M9 16h4" />
                    </svg>
                    View Task Board
                  </button>
                )}
              </div>

              {!canViewTasks && !registrationLoading && (
                <div className="event-detail-tasks-locked">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
                    <rect x="5" y="11" width="14" height="10" rx="2" />
                    <path d="M8 11V7a4 4 0 1 1 8 0v4" />
                    <circle cx="12" cy="16" r="1.25" fill="currentColor" stroke="none" />
                  </svg>
                  <p>Task details are only visible to registered participants and organizers.</p>
                </div>
              )}

              {canViewTasks && tasksLoading && (
                <p className="event-detail-muted">Loading tasks...</p>
              )}

              {canViewTasks && !tasksLoading && tasks.length === 0 && (
                <p className="event-detail-muted">No tasks have been added to this event yet.</p>
              )}

              {canViewTasks && !tasksLoading && tasks.length > 0 && (
                <ul className="event-detail-tasks-list" aria-label="Event tasks">
                  {flattenTasks(tasks).map(({ task, depth }) => (
                    <li
                      key={task.id}
                      className="event-detail-task-item"
                      style={{ '--task-depth': depth } as React.CSSProperties}
                    >
                      <span className="event-detail-task-bullet" aria-hidden />
                      <span className="event-detail-task-title">{task.title}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </article>
        )}
      </main>

      <footer className="event-detail-footer">
        <p>ScottyConnect · Carnegie Mellon University</p>
      </footer>
    </div>
  )
}
