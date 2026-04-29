import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import StorageUtil from '../common/StorageUtil'
import { useNetworking } from '../hooks/useNetworking'
import { AlertBanner } from '../components/networking/AlertBanner'
import { apiUrl } from '../services/Config'
import {
  authHeaders,
  generateTimeSlots,
  getFutureDateStrings,
  getDateLabel,
  isTimePastInMV,
  buildScheduledAt
} from '../utils/networkingUtils'
import type { UserProfile } from '../utils/networkingUtils'
import '../styles/Networking.css'

export default function NetworkingPage() {
  const {
    discoverUsers,
    loading,
    fetchNetworkingData
  } = useNetworking()

  // Profile state
  const [bio, setBio] = useState('')
  const [tagsInput, setTagsInput] = useState('')

  // Selection state
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedTime, setSelectedTime] = useState('')
  const [timeDropdownOpen, setTimeDropdownOpen] = useState(false)
  const [sessionError, setSessionError] = useState(false)

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [targetUser, setTargetUser] = useState<UserProfile | null>(null)
  const [busySlots, setBusySlots] = useState<Set<string>>(new Set())

  const [message, setMessage] = useState('')
  const [alertBox, setAlertBox] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const [discoverRoleFilter, setDiscoverRoleFilter] = useState('')
  const [discoverTagFilter, setDiscoverTagFilter] = useState('')

  // Derived filters
  const uniqueRoles = useMemo(() => {
    const roles = new Set<string>()
    discoverUsers.forEach(u => {
      if (u.role?.trim()) roles.add(u.role.trim().toUpperCase())
    })
    return Array.from(roles).sort()
  }, [discoverUsers])

  const uniqueTags = useMemo(() => {
    const tags = new Set<string>()
    // Add tags from all users
    discoverUsers.forEach(u => {
      (u.tags || []).forEach(t => {
        const s = t.trim()
        if (s) tags.add(s)
      })
    })
    // Also include what the user is currently typing for a live feel
    tagsInput.split(',').forEach(t => {
      const s = t.trim()
      if (s) tags.add(s)
    })
    return Array.from(tags).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
  }, [discoverUsers, tagsInput])

  const filteredDiscoverUsers = useMemo(() => {
    const me = StorageUtil.getUser()
    return discoverUsers
      .filter(u => u.id !== me?.id) // Filter out self from discovery list
      .filter(u => {
        if (discoverRoleFilter && u.role?.trim().toUpperCase() !== discoverRoleFilter.toUpperCase()) return false
        if (discoverTagFilter) {
          const want = discoverTagFilter.trim().toLowerCase()
          if (!(u.tags || []).map(t => t.trim().toLowerCase()).includes(want)) return false
        }
        return true
      })
      .sort((a, b) => (a.username || '').localeCompare(b.username || '', undefined, { sensitivity: 'base' }))
  }, [discoverUsers, discoverRoleFilter, discoverTagFilter])

  function showAlertBox(type: 'success' | 'error', text: string) {
    setAlertBox({ type, text })
    setTimeout(() => setAlertBox(null), 3500)
  }

  useEffect(() => {
    const init = async () => {
      const result = await fetchNetworkingData()
      if (result.error === 'No user session') {
        setSessionError(true)
      } else if (result.me) {
        setBio(result.me.bio || '')
        setTagsInput(result.me.tags ? result.me.tags.join(', ') : '')
      }
    }
    init()
  }, [fetchNetworkingData])

  async function openInviteModal(user: UserProfile) {
    const me = StorageUtil.getUser()
    if (!me) return

    setTargetUser(user)
    setSelectedDate('')
    setSelectedTime('')
    setTimeDropdownOpen(false)
    setIsModalOpen(true)

    try {
      const [res1, res2] = await Promise.all([
        fetch(apiUrl(`/api/networking/busy-slots/${me.id}`), { headers: authHeaders() }),
        fetch(apiUrl(`/api/networking/busy-slots/${user.id}`), { headers: authHeaders() })
      ])
      const data1 = await res1.json()
      const data2 = await res2.json()
      setBusySlots(new Set([...(data1.busy_slots || []), ...(data2.busy_slots || [])]))
    } catch (err) {
      console.error("Failed to fetch busy slots", err)
    }
  }

  async function handleUpdateProfile() {
    const user = StorageUtil.getUser()
    if (!user?.id) return

    try {
      const res = await fetch(apiUrl('/api/accounts/profile'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          bio: bio,
          tags: tagsInput.split(',').map(t => t.trim()).filter(t => t)
        })
      })
      if (res.ok) {
        setMessage("Profile updated successfully!")
        setTimeout(() => setMessage(''), 3000)
        fetchNetworkingData()
      }
    } catch (err) {
      setMessage("Failed to update profile.")
    }
  }

  async function handleSendInvite() {
    if (!selectedDate || !selectedTime || !targetUser) return

    try {
      const scheduled_at = buildScheduledAt(selectedDate, selectedTime)

      const res = await fetch(apiUrl('/api/networking/invite'), {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({ receiver_id: targetUser.id, scheduled_at })
      })
      const data = await res.json()
      if (res.ok) {
        showAlertBox('success', "Invitation sent!")
        setIsModalOpen(false)
        fetchNetworkingData(false) // Refresh appointments but skip discovery
      } else {
        const failureMessage = data.message?.includes('at most 3 distinct alumni per day')
          ? "You have exceeded your invitation cap for today."
          : (data.message || "Failed to send invitation.")
        showAlertBox('error', failureMessage)
      }
    } catch (err) {
      showAlertBox('error', "Error connecting to server.")
    }
  }

  if (sessionError) return (
    <div className="networking-page">
      <div className="auth-error" style={{ textAlign: 'center', padding: '40px' }}>
        <h2>Session Update Required</h2>
        <button className="book-btn" onClick={() => { StorageUtil.removeUser(); window.location.href = '/login'; }}>
          Log Out & Log In Again
        </button>
      </div>
    </div>
  )

  if (loading && discoverUsers.length === 0) return <div className="networking-page">Loading networking hub...</div>

  return (
    <div className="networking-page">
      {alertBox && <AlertBanner type={alertBox.type} text={alertBox.text} onClose={() => setAlertBox(null)} />}

      <header className="networking-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <Link to="/mainpage" className="tag-badge" style={{ textDecoration: 'none', padding: '8px 16px' }}>
            ← Back to Dashboard
          </Link>
          <Link to="/my-meetings" className="book-btn" style={{ width: 'auto', padding: '8px 20px', textDecoration: 'none' }}>
            My Meetings
          </Link>
        </div>
        <h1>Networking Hub</h1>
        <p>Connect with peers and alumni across CMU-SV at the student lounge</p>
        {message && <div className="auth-success" style={{ marginTop: '20px' }}>{message}</div>}
      </header>

      <section className="profile-card">
        <h2>{StorageUtil.getUser()?.username}'s Networking Blueprint</h2>
        <div className="profile-form">
          <div className="profile-form-group">
            <label>Professional Bio</label>
            <textarea value={bio} onChange={e => setBio(e.target.value)} rows={3} placeholder="Tell others what you're working on..." />
          </div>
          <div className="profile-form-group">
            <label>Interest Tags (comma separated)</label>
            <textarea value={tagsInput} onChange={e => setTagsInput(e.target.value)} rows={3} placeholder="e.g. AI, Product Management, Startup" />
            <div className="tag-preview">
              {tagsInput.split(',').map(t => t.trim()).filter(t => t).map(t => (
                <span key={t} className="tag-badge">{t}</span>
              ))}
            </div>
            <button className="book-btn" onClick={handleUpdateProfile} style={{ marginTop: '12px' }}>Update Profile</button>
          </div>
        </div>
      </section>

      <section className="discover-section">
        <h2>Discover People</h2>
        <div className="discover-filters">
          <div className="discover-filter-field">
            <label>Role</label>
            <select className="discover-select" value={discoverRoleFilter} onChange={e => setDiscoverRoleFilter(e.target.value)}>
              <option value="">All roles</option>
              {uniqueRoles.map(role => <option key={role} value={role}>{role}</option>)}
            </select>
          </div>
          <div className="discover-filter-field">
            <label>Tag</label>
            <select className="discover-select" value={discoverTagFilter} onChange={e => setDiscoverTagFilter(e.target.value)}>
              <option value="">All tags</option>
              {uniqueTags.map(tag => <option key={tag} value={tag}>{tag}</option>)}
            </select>
          </div>
        </div>

        {filteredDiscoverUsers.length === 0 ? (
          <div className="discover-empty">No results found for these filters.</div>
        ) : (
          <ul className="discover-list">
            {filteredDiscoverUsers.map(user => (
              <li key={user.id} className="discover-list-row">
                <div className="discover-list-main">
                  <div className="discover-list-title-row">
                    <div className="discover-list-name-group">
                      <h3 className="discover-list-name">{user.username}</h3>
                      <span className="user-role-badge">{user.role}</span>
                    </div>
                  </div>
                  <p className="discover-list-bio">{user.bio || 'Professional in the making. Connect to learn more about my journey.'}</p>
                  <div className="user-tags">
                    {(user.tags || []).map(t => <span key={t} className="tag-badge">{t}</span>)}
                  </div>
                </div>

                <div className="discover-list-actions">
                  <button className="book-btn discover-list-cta" onClick={() => openInviteModal(user)}>Propose Coffee Chat</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {isModalOpen && targetUser && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Propose Coffee Chat with {targetUser.username}</h2>
              <button className="close-modal-btn" onClick={() => setIsModalOpen(false)}>&times;</button>
            </div>
            <div className="modal-body">
              <div className="date-time-picker">
                <label>Choose a date</label>
                <input
                  type="date"
                  min={getFutureDateStrings(1)[0]}
                  max={getFutureDateStrings(14)[13]}
                  value={selectedDate}
                  onChange={e => { setSelectedDate(e.target.value); setSelectedTime(''); setTimeDropdownOpen(false); }}
                />
              </div>
              <div className="date-time-picker">
                <label>Choose a time</label>
                <button type="button" className={`time-dropdown-button ${!selectedDate ? 'disabled' : ''}`} onClick={() => setTimeDropdownOpen(!timeDropdownOpen)} disabled={!selectedDate}>
                  {selectedTime || 'Select a time'} <span className="dropdown-arrow">▾</span>
                </button>
                {timeDropdownOpen && selectedDate && (
                  <div className="time-dropdown-menu">
                    {generateTimeSlots().map(time => {
                      const dateLabel = getDateLabel(selectedDate)
                      const isBusy = busySlots.has(`${dateLabel} @ ${time}`) || isTimePastInMV(selectedDate, time)
                      return (
                        <button key={time} type="button" className={`time-dropdown-item ${selectedTime === time ? 'selected' : ''} ${isBusy ? 'busy' : ''}`} onClick={() => { if (!isBusy) { setSelectedTime(time); setTimeDropdownOpen(false); } }} disabled={isBusy}>
                          {time}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
            <div className="modal-footer">
              <button className="secondary-btn" onClick={() => setIsModalOpen(false)}>Cancel</button>
              <button className="book-btn" disabled={!selectedDate || !selectedTime} onClick={handleSendInvite}>Send Invitation</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
