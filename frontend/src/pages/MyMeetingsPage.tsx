import { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import StorageUtil from '../common/StorageUtil'
import { useNetworking } from '../hooks/useNetworking'
import { AlertBanner } from '../components/networking/AlertBanner'
import {
  authHeaders,
  formatScheduledAt
} from '../utils/networkingUtils'
import type { Appointment } from '../utils/networkingUtils'
import '../styles/MyEvents.css'
import { apiUrl } from '../services/Config'
import '../styles/MyMeetings.css'

type TabType = 'upcoming' | 'past'

const STATUS_PRIORITY: Record<Appointment['status'], number> = {
  ACCEPTED: 0,
  PENDING: 1,
  DECLINED: 2,
  CANCELLED: 3,
}

const backSvg = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M19 12H5M12 19l-7-7 7-7" />
  </svg>
)

export default function MyMeetingsPage() {
  const navigate = useNavigate()
  const { appointments, loading, fetchNetworkingData } = useNetworking()

  const [activeTab, setActiveTab] = useState<TabType>('upcoming')
  const [alertBox, setAlertBox] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [message, setMessage] = useState('')

  const user = StorageUtil.getUser()

  useEffect(() => {
    if (!user?.id) {
      navigate('/login')
      return
    }
    fetchNetworkingData(false) // Fetch only appointments
  }, [fetchNetworkingData, navigate, user?.id])

  const isPast = (scheduledAt: string) => new Date(scheduledAt) < new Date()

  const processedMeetings = useMemo(() => {
    const active = appointments.filter(a => a.status !== 'CANCELLED')
    const upcoming = active
      .filter(a => !isPast(a.scheduled_at))
      .sort((a, b) => STATUS_PRIORITY[a.status] - STATUS_PRIORITY[b.status] || a.scheduled_at.localeCompare(b.scheduled_at))

    const past = active
      .filter(a => isPast(a.scheduled_at))
      .sort((a, b) => STATUS_PRIORITY[a.status] - STATUS_PRIORITY[b.status] || b.scheduled_at.localeCompare(a.scheduled_at))

    return { upcoming, past, total: active.length }
  }, [appointments])

  const displayed = activeTab === 'upcoming' ? processedMeetings.upcoming : processedMeetings.past

  async function handleRespond(inviteId: string, accept: boolean) {
    try {
      const res = await fetch(apiUrl('/api/networking/respond'), {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({ invite_id: inviteId, accept })
      })
      if (res.ok) {
        const msg = accept ? 'Meeting accepted!' : 'Meeting declined.'
        setMessage(msg)
        setAlertBox({ type: 'success', text: msg })
        setTimeout(() => setMessage(''), 3000)
        fetchNetworkingData(false)
      } else {
        const data = await res.json()
        setAlertBox({ type: 'error', text: data.message || 'Failed to respond' })
      }
    } catch {
      setAlertBox({ type: 'error', text: 'Connection error' })
    }
  }

  async function handleCancel(inviteId: string) {
    try {
      const res = await fetch(apiUrl('/api/networking/cancel'), {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({ invite_id: inviteId })
      })
      if (res.ok) {
        setAlertBox({ type: 'success', text: 'Invitation cancelled' })
        fetchNetworkingData(false)
      } else {
        const data = await res.json()
        setAlertBox({ type: 'error', text: data.message || 'Failed to cancel' })
      }
    } catch {
      setAlertBox({ type: 'error', text: 'Connection error' })
    }
  }

  if (loading && appointments.length === 0) {
    return (
      <div className="me-page">
        <main className="me-content"><div className="mm-loading"><div className="mm-spinner" /><p>Loading...</p></div></main>
      </div>
    )
  }

  return (
    <div className="me-page">
      {alertBox && <AlertBanner type={alertBox.type} text={alertBox.text} onClose={() => setAlertBox(null)} classNamePrefix="meetings" />}

      <header className="me-header">
        <div className="me-header-inner">
          <Link to="/networking" className="me-back">{backSvg} Networking Hub</Link>
        </div>
      </header>

      <main className="me-content">
        <h1 className="me-title">My Coffee Chats</h1>
        <p className="me-subtitle">Upcoming and past coffee chats.</p>
        <p className="me-subtitle mm-stats-line">
          <strong>{processedMeetings.total}</strong> total · <strong>{processedMeetings.upcoming.length}</strong> upcoming · <strong>{processedMeetings.past.length}</strong> past
        </p>

        {message && <div className="mm-toast">{message}</div>}

        <div className="me-tabs" role="tablist">
          <button className={`me-tab ${activeTab === 'upcoming' ? 'me-tab-active' : ''}`} onClick={() => setActiveTab('upcoming')}>Upcoming</button>
          <button className={`me-tab ${activeTab === 'past' ? 'me-tab-active' : ''}`} onClick={() => setActiveTab('past')}>Past</button>
        </div>

        <section className="me-section">
          {displayed.length === 0 ? (
            <div className="me-empty"><p>No meetings found.</p></div>
          ) : (
            <ul className="me-event-list">
              {displayed.map(appt => {
                const isSender = appt.sender_id === user?.id
                const otherName = isSender ? appt.receiver_name : appt.sender_name
                const pastMeeting = isPast(appt.scheduled_at)

                return (
                  <li key={appt.id}>
                    <article className={`me-event-card ${pastMeeting ? 'mm-meeting--past' : ''}`}>
                      <div className="me-event-top">
                        <div className="mm-meeting-row">
                          <div className="me-event-body">
                            <h3 className="me-event-title">{otherName}</h3>
                            <p className="me-event-meta">{isSender ? 'Outgoing' : 'Incoming'}</p>
                            <p className="me-event-meta mm-meeting-meta-row">{formatScheduledAt(appt.scheduled_at)}</p>
                          </div>
                        </div>
                        <span className={`me-status-badge mm-status-${appt.status.toLowerCase()}`}>{appt.status}</span>
                      </div>

                      {appt.status === 'PENDING' && !pastMeeting && (
                        <div className="me-event-actions">
                          {isSender ? (
                            <button className="me-action-btn me-action-secondary" onClick={() => handleCancel(appt.id)}>Cancel invite</button>
                          ) : (
                            <>
                              <button className="me-action-btn me-action-publish" onClick={() => handleRespond(appt.id, true)}>Accept</button>
                              <button className="me-action-btn me-action-danger" onClick={() => handleRespond(appt.id, false)}>Decline</button>
                            </>
                          )}
                        </div>
                      )}

                      {appt.status === 'ACCEPTED' && !pastMeeting && (
                        <div className="me-event-actions">
                          <button className="me-action-btn me-action-secondary" onClick={() => handleCancel(appt.id)}>Cancel appointment</button>
                        </div>
                      )}
                    </article>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
