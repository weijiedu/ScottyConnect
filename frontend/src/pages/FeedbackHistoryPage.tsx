import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import StorageUtil from '../common/StorageUtil'
import { apiUrl } from '../services/Config'
import { getLifecycleClockSearch } from '../services/LifecycleService'
import '../styles/FeedbackHistory.css'

interface FeedbackItem {
  id: string
  event_id: string
  rating: number
  comment: string
  created_at: string
}

interface EventInfo {
  title: string
}

export default function FeedbackHistoryPage() {
  const navigate = useNavigate()
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([])
  const [eventInfoMap, setEventInfoMap] = useState<Record<string, EventInfo>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchAll()
  }, [])

  async function fetchAll() {
    const token = StorageUtil.getToken()
    if (!token) {
      setError('You must be logged in to view your feedback history.')
      setLoading(false)
      return
    }

    try {
      // fetch the user's feedback history
      const feedbackRes = await fetch(apiUrl('/api/feedback/me'), {
        headers: { Authorization: `Bearer ${token}` },
      })
      const feedbackData = await feedbackRes.json()
      if (!feedbackRes.ok) {
        setError(feedbackData.message || 'Failed to load feedback history.')
        setLoading(false)
        return
      }

      const items: FeedbackItem[] = feedbackData.feedbacks
      setFeedbacks(items)

      if (items.length === 0) {
        setLoading(false)
        return
      }

      // fetch all unique events in parallel
      const uniqueEventIds = [...new Set(items.map(f => f.event_id))]
      const eventResponses = await Promise.all(
        uniqueEventIds.map(id =>
          fetch(apiUrl(`/api/lifecycle/events/${id}${getLifecycleClockSearch()}`), {
            headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          })
        )
      )

      // Build eventId -> EventInfo lookup
      const infoMap: Record<string, EventInfo> = {}
      await Promise.all(
        eventResponses.map(async (res, i) => {
          const data = await res.json()
          if (data.event) {
            infoMap[uniqueEventIds[i]] = { title: data.event.title }
          }
        })
      )

      setEventInfoMap(infoMap)
    } catch {
      setError('Error connecting to server.')
    } finally {
      setLoading(false)
    }
  }

  function formatDate(isoString: string): string {
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
    <div className="feedback-page">
      <div className="feedback-container">
        <div className="feedback-top-bar">
          <Link to="/mainpage" className="feedback-back-button">
            ← Back to Dashboard
          </Link>
        </div>

        <h1 className="feedback-title">Feedback History</h1>

        <section className="feedback-section">
          <h2 className="feedback-section-title">Past submissions</h2>

          {loading && <p className="feedback-help-text">Loading...</p>}

          {error && <p className="feedback-help-text">{error}</p>}

          {!loading && !error && feedbacks.length === 0 && (
            <p className="feedback-history-empty">
              You haven't submitted any feedback yet.
            </p>
          )}

          {!loading && !error && feedbacks.length > 0 && (
            <ul className="feedback-history-list">
              {feedbacks.map(item => {
                const info = eventInfoMap[item.event_id]
                return (
                  <li
                    key={item.id}
                    className="feedback-history-item"
                    onClick={() => navigate(`/events/${item.event_id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="feedback-history-item-header">
                      <p className="feedback-history-event">
                        {info?.title ?? 'Loading event...'}
                      </p>
                      <p className="feedback-history-date">{formatDate(item.created_at)}</p>
                    </div>
                    <p className="feedback-history-rating">Rating: {item.rating} / 5</p>
                    {item.comment && (
                      <p className="feedback-history-snippet">{item.comment}</p>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
