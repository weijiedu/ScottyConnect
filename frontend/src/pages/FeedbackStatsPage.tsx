import { useState, useEffect } from 'react'
import StorageUtil from '../common/StorageUtil'
import { apiUrl } from '../services/Config'
import type { StoredEvent } from './CreateEventPage'
import '../styles/FeedbackStats.css'

type FeedbackItem = {
  id: string
  event_id: string
  participant_id: string
  rating: number
  comment: string
  created_at: string
}

type FeedbackStatsProps = {
  event: StoredEvent
  onClose: () => void
}

function FeedbackStats({ event, onClose }: FeedbackStatsProps) {
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([])
  const [userMap, setUserMap] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchAll()
  }, [event.id])

  async function fetchAll() {
    const token = StorageUtil.getToken()
    if (!token) {
      setError('Not authenticated.')
      setLoading(false)
      return
    }
    try {
      const [feedbackRes, usersRes] = await Promise.all([
        fetch(apiUrl(`/api/feedback/events/${event.id}`), {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(apiUrl('/api/accounts/discover')),
      ])
      const feedbackData = await feedbackRes.json()
      const usersData = await usersRes.json()

      if (feedbackRes.ok) {
        setFeedbacks(feedbackData.feedbacks)
      } else {
        setError(feedbackData.message || 'Failed to load feedback.')
      }

      const map: Record<string, string> = {}
      for (const user of usersData.users ?? []) {
        map[user.id] = user.username
      }
      setUserMap(map)
    } catch {
      setError('Error connecting to server.')
    } finally {
      setLoading(false)
    }
  }

  const averageRating =
    feedbacks.length > 0
      ? (feedbacks.reduce((sum, f) => sum + f.rating, 0) / feedbacks.length).toFixed(1)
      : null

  function formatEventTime(ev: StoredEvent): string {
    const d = new Date(ev.date + 'T00:00:00')
    const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    if (ev.startTime && ev.endTime) {
      return `${dateStr}, ${formatTime(ev.startTime)} – ${formatTime(ev.endTime)}`
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

function formatSubmittedAt(isoString: string): string {
  const pdt = new Date(new Date(isoString).getTime() - 14 * 60 * 60 * 1000)
  return pdt.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'UTC',
  })
}

  return (
    <div className="event-feedback-modal-overlay" onClick={onClose}>
      <div className="event-feedback-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="event-feedback-top-bar">
          <button type="button" className="event-feedback-back-button" onClick={onClose}>
            ← Close
          </button>
        </div>

        <h1 className="event-feedback-title">Event Feedback Overview</h1>

        <section className="event-feedback-summary">
          <div className="event-feedback-row">
            <span className="event-feedback-label">Event Name:</span>
            <span>{event.title}</span>
          </div>
          <div className="event-feedback-row">
            <span className="event-feedback-label">Event Time:</span>
            <span>{formatEventTime(event)}</span>
          </div>
          <div className="event-feedback-row">
            <span className="event-feedback-label">Average Rating:</span>
            <span>{averageRating !== null ? `${averageRating} / 5.0` : '—'}</span>
          </div>
        </section>

        <section className="event-feedback-list-section">
          <h2 className="event-feedback-section-title">Submitted Feedback</h2>

          {loading && (
            <p className="event-feedback-empty">Loading feedback...</p>
          )}
          {error && (
            <p className="event-feedback-empty">{error}</p>
          )}
          {!loading && !error && feedbacks.length === 0 && (
            <p className="event-feedback-empty">No feedback submitted yet.</p>
          )}

          {!loading && !error && feedbacks.length > 0 && (
            <div className="event-feedback-list">
              {feedbacks.map((item) => (
                <div key={item.id} className="event-feedback-card">
                  <div className="event-feedback-row">
                    <span className="event-feedback-label">User:</span>
                    <span>{userMap[item.participant_id] ?? 'Unknown'}</span>
                  </div>
                  <div className="event-feedback-row">
                    <span className="event-feedback-label">Rating:</span>
                    <span>{item.rating} / 5</span>
                  </div>
                  {item.comment && (
                    <div className="event-feedback-text-block">
                      <span className="event-feedback-label">Feedback:</span>
                      <p className="event-feedback-text">{item.comment}</p>
                    </div>
                  )}
                  <div className="event-feedback-row">
                    <span className="event-feedback-label">Submitted At:</span>
                    <span>{formatSubmittedAt(item.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default FeedbackStats
