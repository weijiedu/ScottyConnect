import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import StorageUtil, { type RecommendationStrategy } from '../common/StorageUtil'
import {
  listPublishedEvents,
  listMyEvents,
  apiEventToStored,
  syncExpiredPublishedEvents,
  getEventTags,
  type PublicEvent,
} from '../services/LifecycleService'
import {
  getRecommendations,
  getUserPreference,
  setUserPreference,
} from '../services/RecommendationService'
import { getRegisteredUsers } from '../services/AttendanceService'
import RecommendationSettingsModal from '../components/RecommendationSettingsModal'
import EventTagDisplay from '../components/EventTagDisplay'
import type { StoredEvent } from '../types/event'
import '../styles/Main.css'
import '../styles/Settings.css'

const STRATEGY_OPTIONS: { value: RecommendationStrategy; label: string }[] = [
  { value: 'tag', label: 'Tag' },
  { value: 'popularity', label: 'Popularity' },
  { value: 'hybrid', label: 'Hybrid' },
]

/** Convert HH:mm (24h) to h:mm AM/PM */
function formatTime12h(hhmm: string): string {
  const parts = hhmm.split(':')
  if (parts.length < 2) return hhmm
  const hour = parseInt(parts[0], 10)
  const min = parts[1]
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const h12 = hour % 12 || 12
  return `${h12}:${min} ${ampm}`
}

function formatEventDate(ev: StoredEvent): string {
  const d = new Date(ev.date + 'T00:00:00')
  const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  if (ev.startTime) {
    const startLabel = formatTime12h(ev.startTime)
    if (ev.endTime) {
      return `${dateStr} · ${startLabel} – ${formatTime12h(ev.endTime)}`
    }
    return `${dateStr} · ${startLabel}`
  }
  return dateStr
}

function formatSpots(ev: StoredEvent): string {
  if (ev.status != "published") return 'Closed'
  if (ev.registeredCount) return `${ev.registeredCount} going`
  return 'Open'
}

/**
 * Main feed only: treat an event as past once local `date` + `endTime` has passed.
 * If date or endTime is missing/unparseable, the event is kept (demo-safe default).
 */
function isMainPageEventStillActive(ev: PublicEvent): boolean {
  const d = ev.date?.trim()
  const t = ev.endTime?.trim()
  if (!d || !t) return true
  const end = new Date(`${d}T${t}`)
  if (Number.isNaN(end.getTime())) return true
  return end.getTime() > new Date().getTime()
}

export default function MainPage() {
  const userId = StorageUtil.getUser().id
  const isLoggedIn = !!userId && !!StorageUtil.getToken()

  const [events, setEvents] = useState<StoredEvent[]>([])
  const [eventsLoading, setEventsLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [myCreatedCount, setMyCreatedCount] = useState<number | null>(null)
  const [strategy, setStrategy] = useState<RecommendationStrategy>(() =>
    StorageUtil.getStrategy(),
  )
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [refreshNonce, setRefreshNonce] = useState(0)
  const [tagsByEventId, setTagsByEventId] = useState<Record<string, string[]>>({})

  function handleStrategyChange(next: RecommendationStrategy) {
    setStrategy(next)
    StorageUtil.setStrategy(next)
    if (isLoggedIn && userId) {
      // Fire-and-forget persist; local UI already reflects the choice.
      setUserPreference(userId, next).catch(() => {
        // Network/server issue — keep local selection; user can retry via settings.
      })
    }
  }

  function handleLogout() {
    StorageUtil.clearAll()
  }

  // Sync local strategy with the backend-stored preference on login.
  useEffect(() => {
    if (!isLoggedIn || !userId) return
    let cancelled = false
    ;(async () => {
      try {
        const serverStrategy = await getUserPreference(userId)
        if (!cancelled) {
          setStrategy(serverStrategy)
          StorageUtil.setStrategy(serverStrategy)
        }
      } catch {
        // Keep whatever is in localStorage if the fetch fails.
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isLoggedIn, userId])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!cancelled) {
        setEventsLoading(true)
      }
      try {
        if (isLoggedIn && userId) {
          try {
            await syncExpiredPublishedEvents()
          } catch {
            // Best-effort: ignore sync failures and proceed.
          }
          const list = (await getRecommendations(userId, strategy)).filter(isMainPageEventStillActive)
          await Promise.all(list.map(async (ev) => {
            const users = await getRegisteredUsers(ev.id)
            ev.registeredCount = users.length
          }))
          if (!cancelled) {
            setEvents(list.map(apiEventToStored))
            setLoadError('')
          }
        } else {
          const list = (await listPublishedEvents()).filter(isMainPageEventStillActive)
          await Promise.all(list.map(async (ev) => {
            const users = await getRegisteredUsers(ev.id)
            ev.registeredCount = users.length
          }))
          if (!cancelled) {
            setEvents(list.map(apiEventToStored))
            setLoadError('')
          }
        }
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : 'Failed to load events')
      } finally {
        if (!cancelled) {
          setEventsLoading(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isLoggedIn, userId, strategy, refreshNonce])

  // Fetch event tags for all displayed events, in parallel.
  useEffect(() => {
    if (events.length === 0) {
      setTagsByEventId({})
      return
    }
    let cancelled = false
    ;(async () => {
      const results = await Promise.all(
        events.map((ev) =>
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
  }, [events])

  useEffect(() => {
    if (!StorageUtil.getToken()) {
      setMyCreatedCount(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const mine = await listMyEvents()
        if (!cancelled) setMyCreatedCount(mine.length)
      } catch {
        if (!cancelled) setMyCreatedCount(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="main-page">
      <header className="main-header">
        <div className="main-header-inner">
          <Link to="/mainpage" className="main-brand">
            <img
              src="/scotty_connect_square.png"
              alt=""
              className="main-brand-logo"
              width={40}
              height={40}
            />
            <span className="main-brand-text">ScottyConnect</span>
          </Link>
          <Link to="/" className="main-nav-link" onClick={handleLogout}>
            Logout
          </Link>
        </div>
      </header>

      {isLoggedIn && userId && (
        <RecommendationSettingsModal
          isOpen={settingsOpen}
          userId={userId}
          onClose={() => setSettingsOpen(false)}
          onSaved={() => {
            // Re-fetch recommendations to reflect the new tag set.
            setRefreshNonce((n) => n + 1)
          }}
        />
      )}

      <main className="main-content">

        <section className="main-section" aria-labelledby="actions-heading">
          <div className="main-section-head">
            <h2 id="actions-heading" className="main-section-title">
              Quick Actions
            </h2>
            <p className="main-section-desc">Shortcuts for networking, feedback, publishing, and attendance</p>
          </div>
          <ul className="main-action-grid">
            <li>
              <Link to="/my-events" className="main-action-card">
                <span className="main-action-icon" aria-hidden>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                    <rect x="3" y="5" width="18" height="16" rx="2" />
                    <path d="M16 3v4M8 3v4M3 10h18" />
                    <path d="M8 14h2M12 14h2M16 14h2M8 17h2M12 17h2" />
                  </svg>
                </span>
                <span className="main-action-label">My Events{myCreatedCount != null && myCreatedCount > 0 && ` (${myCreatedCount})`}</span>
                <span className="main-action-hint">Events you organized</span>
              </Link>
            </li>
            <li>
              <Link to="/publish-event" className="main-action-card">
                <span className="main-action-icon" aria-hidden>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 8v8M8 12h8" />
                  </svg>
                </span>
                <span className="main-action-label">Publish new event</span>
                <span className="main-action-hint">Create and manage lifecycle</span>
              </Link>
            </li>
            <li>
              <Link to="/networking" className="main-action-card">
                <span className="main-action-icon" aria-hidden>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                </span>
                <span className="main-action-label">Networking</span>
                <span className="main-action-hint">Meet peers and mentors</span>
              </Link>
            </li>
            <li>
              <Link to="/feedback" className="main-action-card">
                <span className="main-action-icon" aria-hidden>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                </span>
                <span className="main-action-label">Feedback</span>
                <span className="main-action-hint">Reviews and suggestions</span>
              </Link>
            </li>
          </ul>
        </section>

        <section className="main-section" aria-labelledby="events-heading">
          <div className="main-section-head">
            <h2 id="events-heading" className="main-section-title">
              {isLoggedIn ? 'Events Recommended for You' : 'Active events'}
            </h2>
            <p className="main-section-desc">
              {isLoggedIn
                ? 'Published events ranked by your selected strategy'
                : 'Open registrations and upcoming sessions'}
            </p>
            {isLoggedIn && (
              <div className="main-strategy-row">
                <div
                  className="main-strategy-selector"
                  role="radiogroup"
                  aria-label="Recommendation strategy"
                >
                  {STRATEGY_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      role="radio"
                      aria-checked={strategy === opt.value}
                      className={`main-strategy-option${
                        strategy === opt.value ? ' is-active' : ''
                      }`}
                      onClick={() => handleStrategyChange(opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                {strategy === 'tag' && (
                  <button
                    type="button"
                    className="main-strategy-edit-btn"
                    onClick={() => setSettingsOpen(true)}
                  >
                    View / set tag preferences
                  </button>
                )}
              </div>
            )}
          </div>
          {loadError && <p className="main-section-desc" role="alert">{loadError}</p>}
          {eventsLoading && !loadError && (
            <p className="main-section-desc" aria-live="polite">Loading events...</p>
          )}
          <ul className="main-event-list">
            {events.map((ev) => (
              <li key={ev.id}>
                <Link to={`/events/${ev.id}`} className="main-event-link">
                  <article className="main-event-card">
                    <div className="main-event-card-body">
                      <h3 className="main-event-title">{ev.title}</h3>
                      <p className="main-event-meta main-event-meta-primary">{formatEventDate(ev)}</p>
                      {ev.location && <p className="main-event-meta">{ev.location}</p>}
                      {tagsByEventId[ev.id] && tagsByEventId[ev.id].length > 0 && (
                        <div className="main-event-tags">
                          <EventTagDisplay tagIds={tagsByEventId[ev.id]} limit={3} />
                        </div>
                      )}
                    </div>
                    <div className="main-event-card-aside">
                      <span
                        className={`main-event-badge${
                          ev.status !== 'published'
                            ? ' is-closed'
                            : ev.registeredCount
                              ? ' is-going'
                              : ' is-open'
                        }`}
                      >
                        {formatSpots(ev)}
                      </span>
                    </div>
                  </article>
                </Link>
              </li>
            ))}
          </ul>
          {events.length === 0 && !loadError && !eventsLoading && (
            <p className="main-section-desc">No published events yet.</p>
          )}
        </section>

      </main>

      <footer className="main-footer">
        <p>ScottyConnect · Carnegie Mellon University</p>
      </footer>
    </div>
  )
}
