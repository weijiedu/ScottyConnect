import { useState, type FormEvent, type CSSProperties } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  createEvent as createEventAPI,
  setEventTags,
  apiEventToStored,
} from '../services/LifecycleService'
import EventTagSelector from '../components/EventTagSelector'
import { DEFAULT_EVENT_TAG_IDS } from '../common/EventTagDefaults'
import type { EventFormData, StoredEvent } from '../types/event'
import '../styles/CreateEvent.css'

export type { EventFormData, StoredEvent }

/** Same schedule line as the old confirmation page / modal summary */
export function formatPublishedSummaryDate(ev: StoredEvent): string {
  const d = new Date(ev.date + 'T00:00:00')
  const dateStr = d.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
  if (!ev.startTime) return dateStr
  const [h, m] = ev.startTime.split(':')
  const hour = parseInt(h, 10)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const h12 = hour % 12 || 12
  let timeStr = `${h12}:${m} ${ampm}`
  if (ev.endTime) {
    const [eh, em] = ev.endTime.split(':')
    const eHour = parseInt(eh, 10)
    const eAmpm = eHour >= 12 ? 'PM' : 'AM'
    const eH12 = eHour % 12 || 12
    timeStr += ` – ${eH12}:${em} ${eAmpm}`
  }
  return `${dateStr} · ${timeStr}`
}

/** Return value when publish succeeds — triggers the in-form success modal */
export type EventSaveResult = { published: StoredEvent } | undefined

/** Local calendar date YYYY-MM-DD */
function getLocalDateString(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Local time HH:mm for `<input type="time" />` */
function getLocalTimeString(d: Date): string {
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${min}`
}

function parseLocalDateTimeMs(dateStr: string, timeStr: string): number {
  const [Y, M, D] = dateStr.split('-').map(Number)
  const [hh, mm] = timeStr.split(':').map(Number)
  return new Date(Y, M - 1, D, hh, mm, 0, 0).getTime()
}

/** Event start must be strictly after now; end must be strictly after start (same calendar day). */
function isScheduleInFuture(dateStr: string, startTime: string, endTime: string): boolean {
  if (!dateStr || !startTime || !endTime) return false
  const startMs = parseLocalDateTimeMs(dateStr, startTime)
  const endMs = parseLocalDateTimeMs(dateStr, endTime)
  const nowMs = Date.now()
  if (endMs <= startMs) return false
  if (startMs <= nowMs) return false
  return true
}

/** Lexicographic max for equal-length HH:mm strings on the same day. */
function maxTimeHHMM(a: string, b: string): string {
  return a >= b ? a : b
}

function isDateBeforeToday(dateStr: string, todayStr: string): boolean {
  return dateStr !== '' && dateStr < todayStr
}

/** True if start is now or in the past (invalid for new/edited events). */
function isStartNotStrictlyFuture(dateStr: string, startTime: string): boolean {
  if (!dateStr || !startTime) return false
  return parseLocalDateTimeMs(dateStr, startTime) <= Date.now()
}

function isEndNotAfterStart(dateStr: string, startTime: string, endTime: string): boolean {
  if (!dateStr || !startTime || !endTime) return false
  return parseLocalDateTimeMs(dateStr, endTime) <= parseLocalDateTimeMs(dateStr, startTime)
}

const EVENTS_STORAGE_KEY = 'scottyConnectEvents'

function loadEvents(): StoredEvent[] {
  try {
    return JSON.parse(localStorage.getItem(EVENTS_STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

function updateEvent(updated: StoredEvent) {
  const events = loadEvents()
  const idx = events.findIndex((e) => e.id === updated.id)
  if (idx === -1) return
  events[idx] = updated
  localStorage.setItem(EVENTS_STORAGE_KEY, JSON.stringify(events))
}

function deleteEvent(eventId: string) {
  const events = loadEvents().filter((e) => e.id !== eventId)
  localStorage.setItem(EVENTS_STORAGE_KEY, JSON.stringify(events))
}

function findEvent(eventId: string): StoredEvent | undefined {
  return loadEvents().find((e) => e.id === eventId)
}

export { EVENTS_STORAGE_KEY, loadEvents, updateEvent, deleteEvent, findEvent }

const EMPTY_FORM: EventFormData = {
  title: '',
  description: '',
  date: '',
  startTime: '',
  endTime: '',
  location: '',
  capacity: '',
}

export function storedToForm(ev: StoredEvent): EventFormData {
  return {
    title: ev.title,
    description: ev.description,
    date: ev.date,
    startTime: ev.startTime,
    endTime: ev.endTime,
    location: ev.location,
    capacity: ev.capacity != null ? String(ev.capacity) : '',
  }
}

interface EventFormProps {
  initialData?: EventFormData
  initialTagIds?: string[]
  pageTitle: string
  pageSubtitle: string
  backTo: string
  backLabel: string
  onSave: (
    form: EventFormData,
    status: StoredEvent['status'],
    tagIds: string[],
  ) => void | Promise<EventSaveResult>
}

export function EventForm({
  initialData,
  initialTagIds,
  pageTitle,
  pageSubtitle,
  backTo,
  backLabel,
  onSave,
}: EventFormProps) {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [showDraftModal, setShowDraftModal] = useState(false)
  const [showPublishedModal, setShowPublishedModal] = useState(false)
  const [publishedSnapshot, setPublishedSnapshot] = useState<StoredEvent | null>(null)
  const [form, setForm] = useState<EventFormData>(initialData ?? EMPTY_FORM)
  const [selectedTagIds, setSelectedTagIds] = useState<Set<string>>(
    () => new Set(initialTagIds ?? DEFAULT_EVENT_TAG_IDS),
  )

  function toggleTag(tagId: string) {
    setSelectedTagIds((prev) => {
      const next = new Set(prev)
      if (next.has(tagId)) {
        next.delete(tagId)
      } else {
        next.add(tagId)
      }
      return next
    })
  }

  const todayStr = getLocalDateString(new Date())
  const nowTimeStr = getLocalTimeString(new Date())

  const startTimeMin = form.date === todayStr ? nowTimeStr : undefined

  let endTimeMin: string | undefined
  if (!form.date) {
    endTimeMin = undefined
  } else if (form.date === todayStr) {
    endTimeMin = form.startTime ? maxTimeHHMM(nowTimeStr, form.startTime) : nowTimeStr
  } else {
    endTimeMin = form.startTime || undefined
  }

  function update(field: keyof EventFormData, value: string) {
    setForm((prev) => {
      const next: EventFormData = { ...prev, [field]: value }
      if (field === 'date') {
        const t = getLocalDateString(new Date())
        const n = getLocalTimeString(new Date())
        if (value === t) {
          if (next.startTime && next.startTime < n) next.startTime = n
          const endMin =
            next.startTime && next.startTime >= n ? next.startTime : n
          if (next.endTime && next.endTime <= endMin) next.endTime = ''
        }
      }
      if (field === 'startTime' && next.date === getLocalDateString(new Date())) {
        const n = getLocalTimeString(new Date())
        if (value < n) next.startTime = n
      }
      if (field === 'startTime' && next.endTime && next.endTime <= value) {
        next.endTime = ''
      }
      return next
    })
  }

  const scheduleOk = isScheduleInFuture(form.date, form.startTime, form.endTime)

  const warnPastDate = isDateBeforeToday(form.date, todayStr)
  const warnPastStart = isStartNotStrictlyFuture(form.date, form.startTime)
  const warnEndNotAfterStart = isEndNotAfterStart(form.date, form.startTime, form.endTime)

  const isValid =
    form.title.trim() !== '' &&
    form.description.trim() !== '' &&
    form.date !== '' &&
    form.startTime !== '' &&
    form.endTime !== '' &&
    form.location.trim() !== '' &&
    scheduleOk

  async function handleSubmit(status: StoredEvent['status']) {
    if (!isValid) return
    setSubmitting(true)
    try {
      const result = await onSave(form, status, Array.from(selectedTagIds))
      if (status === 'draft') {
        setShowDraftModal(true)
      }
      if (status === 'published' && result?.published) {
        setPublishedSnapshot(result.published)
        setShowPublishedModal(true)
      }
    } finally {
      setSubmitting(false)
    }
  }

  async function onFormSubmit(e: FormEvent) {
    e.preventDefault()
    if (!isValid) return
    setSubmitting(true)
    try {
      const result = await onSave(form, 'published', Array.from(selectedTagIds))
      if (result?.published) {
        setPublishedSnapshot(result.published)
        setShowPublishedModal(true)
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="create-event-page">
      <header className="create-event-header">
        <div className="create-event-header-inner">
          <Link to={backTo} className="create-event-back">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            {backLabel}
          </Link>
        </div>
      </header>

      <main className="create-event-content">
        <h1 className="create-event-title">{pageTitle}</h1>
        <p className="create-event-subtitle">{pageSubtitle}</p>

        <form className="create-event-form" onSubmit={onFormSubmit}>
          <div className="create-event-card">
            <h2 className="create-event-card-title">Event details</h2>
            <div className="create-event-fields">
              <div className="create-event-field">
                <label className="create-event-label" htmlFor="ev-title">
                  Event title <span className="required">*</span>
                </label>
                <input
                  id="ev-title"
                  className="create-event-input"
                  type="text"
                  placeholder="e.g. CMU-SV Carnival"
                  value={form.title}
                  onChange={(e) => update('title', e.target.value)}
                  required
                />
              </div>
              <div className="create-event-field">
                <label className="create-event-label" htmlFor="ev-desc">
                  Description <span className="required">*</span>
                </label>
                <textarea
                  id="ev-desc"
                  className="create-event-textarea"
                  placeholder="Tell attendees what this event is about..."
                  value={form.description}
                  onChange={(e) => update('description', e.target.value)}
                  required
                />
              </div>
              <div className="create-event-field">
                <label className="create-event-label" htmlFor="ev-location">
                  Location <span className="required">*</span>
                </label>
                <input
                  id="ev-location"
                  className="create-event-input"
                  type="text"
                  placeholder="e.g. CMUSV Building 23"
                  value={form.location}
                  onChange={(e) => update('location', e.target.value)}
                  required
                />
              </div>
            </div>
          </div>

          <div className="create-event-card">
            <h2 className="create-event-card-title">Schedule</h2>
            <div className="create-event-fields">
              <div className="create-event-field">
                <label className="create-event-label" htmlFor="ev-date">
                  Date <span className="required">*</span>
                </label>
                <input
                  id="ev-date"
                  className="create-event-input"
                  type="date"
                  min={todayStr}
                  value={form.date}
                  onChange={(e) => update('date', e.target.value)}
                  required
                />
              </div>
              <div className="create-event-row">
                <div className="create-event-field">
                  <label className="create-event-label" htmlFor="ev-start">
                    Start time <span className="required">*</span>
                  </label>
                  <input
                    id="ev-start"
                    className="create-event-input"
                    type="time"
                    min={startTimeMin}
                    value={form.startTime}
                    onChange={(e) => update('startTime', e.target.value)}
                    required
                  />
                </div>
                <div className="create-event-field">
                  <label className="create-event-label" htmlFor="ev-end">
                    End time <span className="required">*</span>
                  </label>
                  <input
                    id="ev-end"
                    className="create-event-input"
                    type="time"
                    min={endTimeMin}
                    value={form.endTime}
                    onChange={(e) => update('endTime', e.target.value)}
                    required
                  />
                </div>
              </div>
              {(warnPastDate || warnPastStart || warnEndNotAfterStart || (form.date && form.startTime && form.endTime && !scheduleOk)) && (
                <div className="create-event-schedule-warnings" role="status">
                  {warnPastDate && (
                    <p className="create-event-schedule-warn">This date is in the past. Choose today or a future date.</p>
                  )}
                  {warnPastStart && (
                    <p className="create-event-schedule-warn">Start time must be in the future.</p>
                  )}
                  {warnEndNotAfterStart && (
                    <p className="create-event-schedule-warn">End time must be after start time.</p>
                  )}
                  {!warnPastDate && !warnPastStart && !warnEndNotAfterStart && form.date && form.startTime && form.endTime && !scheduleOk && (
                    <p className="create-event-schedule-hint">Choose a date and times in the future, with end time after start time.</p>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="create-event-card">
            <h2 className="create-event-card-title">Capacity</h2>
            <div className="create-event-fields">
              <div className="create-event-field">
                <label className="create-event-label" htmlFor="ev-capacity">
                  Maximum attendees
                </label>
                <input
                  id="ev-capacity"
                  className="create-event-input"
                  type="number"
                  min="1"
                  placeholder="Leave blank for unlimited"
                  value={form.capacity}
                  onChange={(e) => update('capacity', e.target.value)}
                  onWheel={(e) => {
                    e.currentTarget.blur()
                  }}
                />
              </div>
            </div>
          </div>

          <div className="create-event-card">
            <h2 className="create-event-card-title">Tags</h2>
            <div className="create-event-fields">
              <EventTagSelector
                selectedTagIds={selectedTagIds}
                onToggle={toggleTag}
              />
            </div>
          </div>

          <div className="create-event-actions">
            <button
              type="submit"
              className="create-event-btn create-event-btn-publish"
              disabled={!isValid || submitting}
            >
              Publish Event
            </button>
            <button
              type="button"
              className="create-event-btn create-event-btn-draft"
              disabled={!isValid || submitting}
              onClick={() => handleSubmit('draft')}
            >
              Save as Draft
            </button>
            <button
              type="button"
              className="create-event-btn create-event-btn-cancel"
              onClick={() => navigate(backTo)}
            >
              Cancel
            </button>
          </div>
        </form>
      </main>

      <footer className="create-event-footer">
        <p>ScottyConnect · Carnegie Mellon University</p>
      </footer>

      {showDraftModal && (
        <div className="draft-modal-overlay" onClick={() => setShowDraftModal(false)}>
          <div className="draft-modal" onClick={(e) => e.stopPropagation()}>
            <div className="draft-modal-icon" aria-hidden>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <path d="M22 4 12 14.01l-3-3" />
              </svg>
            </div>
            <h2 className="draft-modal-title">Draft Saved Successfully</h2>
            <p className="draft-modal-message">
              Your event has been saved as a draft. You can go to My Events to view and edit it later.
            </p>
            <div className="draft-modal-actions">
              <button
                className="draft-modal-btn draft-modal-btn-primary"
                onClick={() => navigate('/my-events')}
              >
                Go to My Events
              </button>
              <button
                className="draft-modal-btn draft-modal-btn-secondary"
                onClick={() => navigate('/mainpage')}
              >
                Back to Home
              </button>
            </div>
          </div>
        </div>
      )}

      {showPublishedModal && publishedSnapshot && (
        <div
          className="draft-modal-overlay"
          onClick={() => {
            setShowPublishedModal(false)
            setPublishedSnapshot(null)
          }}
        >
          <div
            className="draft-modal draft-modal--published"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="published-modal-title"
          >
            <div className="published-modal-celebrate" aria-hidden>
              <div className="published-modal-celebrate__ring" />
              {Array.from({ length: 12 }).map((_, i) => (
                <span
                  key={i}
                  className="published-modal-confetti"
                  style={{ '--n': i } as CSSProperties}
                />
              ))}
              <div className="published-modal-celebrate__icon-wrap">
                <div className="draft-modal-icon published-modal-celebrate__check">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <path d="M22 4 12 14.01l-3-3" />
                  </svg>
                </div>
              </div>
            </div>
            <h2 id="published-modal-title" className="draft-modal-title published-modal-title">
              Event Published Successfully
            </h2>
            <div className="draft-modal-summary">
              <h3 className="draft-modal-summary-title">{publishedSnapshot.title}</h3>
              <p className="draft-modal-summary-meta">{formatPublishedSummaryDate(publishedSnapshot)}</p>
              {publishedSnapshot.location && (
                <p className="draft-modal-summary-meta">{publishedSnapshot.location}</p>
              )}
              {publishedSnapshot.capacity != null && publishedSnapshot.capacity > 0 && (
                <p className="draft-modal-summary-meta">Capacity: {publishedSnapshot.capacity}</p>
              )}
              {publishedSnapshot.description.trim() !== '' && (
                <p className="draft-modal-summary-desc">{publishedSnapshot.description}</p>
              )}
            </div>
            <p className="draft-modal-message">
              You can now go to My Events to manage this event and create event tasks.
            </p>
            <div className="draft-modal-actions">
              <button
                type="button"
                className="draft-modal-btn draft-modal-btn-primary"
                onClick={() => navigate('/my-events')}
              >
                Go to My Events
              </button>
              <button
                type="button"
                className="draft-modal-btn draft-modal-btn-secondary"
                onClick={() => navigate('/mainpage')}
              >
                Back to Home
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function CreateEventPage() {
  const [error, setError] = useState('')

  async function handleSave(
    form: EventFormData,
    status: StoredEvent['status'],
    tagIds: string[],
  ): Promise<EventSaveResult> {
    setError('')
    try {
      const saved = await createEventAPI(form, status as 'draft' | 'published')
      // Save tags (best-effort — don't block event creation success if tags fail).
      if (tagIds.length > 0) {
        try {
          await setEventTags(saved.id, tagIds)
        } catch (tagErr) {
          console.error('Failed to save event tags:', tagErr)
        }
      }
      if (status === 'published') {
        return { published: apiEventToStored(saved) }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create event')
    }
    return undefined
  }

  return (
    <>
      {error && <div className="create-event-error">{error}</div>}
      <EventForm
        pageTitle="Create new event"
        pageSubtitle="Fill in the details below to create a new event for the ScottyConnect community."
        backTo="/mainpage"
        backLabel="Back to home"
        onSave={handleSave}
      />
    </>
  )
}
