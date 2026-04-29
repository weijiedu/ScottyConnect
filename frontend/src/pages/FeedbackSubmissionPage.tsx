import { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import StorageUtil from '../common/StorageUtil'
import { apiUrl } from '../services/Config'
import '../styles/FeedbackSubmission.css'

type NavState = {
  title?: string
  date?: string
  startTime?: string
  endTime?: string
}

type FeedbackStatus = {
  enabled: boolean
  eligible: boolean
}

function formatEventTime(date: string, startTime: string, endTime: string): string {
  const d = new Date(date + 'T00:00:00')
  const dateStr = d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
  if (startTime && endTime) {
    return `${dateStr}, ${formatTime(startTime)} – ${formatTime(endTime)}`
  }
  return dateStr
}

function formatTime(t: string): string {
  const [h, m] = t.split(':')
  const hour = parseInt(h, 10)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const h12 = hour % 12 || 12
  return `${h12}:${m} ${ampm}`
}

export default function FeedbackSubmissionPage() {
  const { eventId } = useParams<{ eventId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const navState = (location.state ?? {}) as NavState

  const [status, setStatus] = useState<FeedbackStatus | null>(null)
  const [alreadySubmitted, setAlreadySubmitted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [rating, setRating] = useState('')
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const username = StorageUtil.getUser()?.username ?? 'Unknown'

  useEffect(() => {
    if (!eventId) return
    loadFeedbackState()
  }, [eventId])

  // Only talks to the feedback module — no lifecycle calls.
  // The feedback_sessions document was created the moment the event ended
  // via the Observer / MessageBus subscription in FeedbackService.processMessage,
  // so this is the single authoritative source for both eligibility and status.
  async function loadFeedbackState() {
    const token = StorageUtil.getToken()
    if (!token) {
      setLoadError('You must be signed in to submit feedback.')
      setLoading(false)
      return
    }

    try {
      const [statusRes, myFeedbackRes] = await Promise.all([
        fetch(apiUrl(`/api/feedback/events/${eventId}/status`), {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(apiUrl(`/api/feedback/events/${eventId}/me`), {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ])

      const statusData = await statusRes.json()
      const myFeedbackData = await myFeedbackRes.json()

      if (statusRes.ok) {
        setStatus({ enabled: statusData.enabled, eligible: statusData.eligible })
      } else {
        setLoadError('Could not load feedback status.')
        return
      }

      if (myFeedbackRes.ok && myFeedbackData.feedback) {
        setAlreadySubmitted(true)
      }
    } catch {
      setLoadError('Error connecting to server.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!rating) {
      setSubmitError('Please select a rating.')
      return
    }
    const token = StorageUtil.getToken()
    if (!token || !eventId) return

    setSubmitting(true)
    setSubmitError('')

    try {
      const res = await fetch(apiUrl(`/api/feedback/events/${eventId}`), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ rating: parseInt(rating, 10), comment }),
      })

      const data = await res.json()

      if (res.ok) {
        setSubmitted(true)
      } else {
        setSubmitError(data.message || 'Failed to submit feedback.')
      }
    } catch {
      setSubmitError('Error connecting to server.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Shared header ──────────────────────────────────────────────
  function Header() {
    return (
      <header className="fs-header">
        <div className="fs-header-inner">
          <button className="fs-back" onClick={() => navigate('/my-events')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Back to My Events
          </button>
        </div>
      </header>
    )
  }

  // ── State screens ──────────────────────────────────────────────

  if (loading) {
    return (
      <div className="fs-page">
        <Header />
        <div className="fs-content">
          <div className="fs-card">
            <div className="fs-state">
              <p className="fs-state-msg">Loading…</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="fs-page">
        <Header />
        <div className="fs-content">
          <div className="fs-card">
            <div className="fs-state">
              <p className="fs-state-msg fs-state-msg--error">{loadError}</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="fs-page">
        <Header />
        <div className="fs-content">
          <div className="fs-card">
            <div className="fs-state">
              <h2 className="fs-state-title">Thank You!</h2>
              <p className="fs-state-msg">Your feedback has been submitted successfully.</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (alreadySubmitted) {
    return (
      <div className="fs-page">
        <Header />
        <div className="fs-content">
          <div className="fs-card">
            <div className="fs-state">
              <h2 className="fs-state-title">Already Submitted</h2>
              <p className="fs-state-msg">You have already submitted feedback for this event.</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (status && !status.enabled) {
    return (
      <div className="fs-page">
        <Header />
        <div className="fs-content">
          <div className="fs-card">
            <div className="fs-state">
              <h2 className="fs-state-title">Not Available Yet</h2>
              <p className="fs-state-msg">Feedback is not yet available for this event.</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (status && !status.eligible) {
    return (
      <div className="fs-page">
        <Header />
        <div className="fs-content">
          <div className="fs-card">
            <div className="fs-state">
              <h2 className="fs-state-title">Not Eligible</h2>
              <p className="fs-state-msg">You must have attended this event to submit feedback.</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Main form ──────────────────────────────────────────────────

  return (
    <div className="fs-page">
      <Header />

      <div className="fs-content">
        <h1 className="fs-title">Submit Feedback</h1>

        <div className="fs-card">
          <section className="fs-section">
            <h2 className="fs-section-title">Event Info</h2>
            <div className="fs-info-row">
              <span className="fs-label">User:</span>
              <span className="fs-value">{username}</span>
            </div>
            {navState.title && (
              <div className="fs-info-row">
                <span className="fs-label">Event:</span>
                <span className="fs-value">{navState.title}</span>
              </div>
            )}
            {navState.date && (
              <div className="fs-info-row">
                <span className="fs-label">Time:</span>
                <span className="fs-value">
                  {formatEventTime(navState.date, navState.startTime ?? '', navState.endTime ?? '')}
                </span>
              </div>
            )}
          </section>

          <section className="fs-section">
            <h2 className="fs-section-title">Your Feedback</h2>

            <form className="fs-form" onSubmit={handleSubmit}>
              <div className="fs-form-group">
                <label htmlFor="rating">Rating (1 to 5)</label>
                <select
                  id="rating"
                  name="rating"
                  required
                  value={rating}
                  onChange={(e) => setRating(e.target.value)}
                >
                  <option value="">Select a rating</option>
                  <option value="1">1 — Very Poor</option>
                  <option value="2">2 — Poor</option>
                  <option value="3">3 — Average</option>
                  <option value="4">4 — Good</option>
                  <option value="5">5 — Excellent</option>
                </select>
              </div>

              <div className="fs-form-group">
                <label htmlFor="comment">Comment</label>
                <textarea
                  id="comment"
                  name="comment"
                  maxLength={1000}
                  placeholder="Share your thoughts about this event…"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                />
                <p className="fs-help-text">Maximum 1000 characters</p>
              </div>

              {submitError && <p className="fs-error">{submitError}</p>}

              <button
                type="submit"
                className="fs-submit-btn"
                disabled={submitting}
              >
                {submitting ? 'Submitting…' : 'Submit Feedback'}
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  )
}
