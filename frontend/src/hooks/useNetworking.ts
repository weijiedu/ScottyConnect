import { useState, useCallback } from 'react'
import StorageUtil from '../common/StorageUtil'
import { authHeaders } from '../utils/networkingUtils'
import { apiUrl } from '../services/Config'
import type { Appointment, UserProfile } from '../utils/networkingUtils'

export function useNetworking() {
  const [appointments, setAppointments] = useState<Appointment[]>(() => {
    const cached = sessionStorage.getItem('scotty_networking_appointments')
    return cached ? JSON.parse(cached) : []
  })
  const [discoverUsers, setDiscoverUsers] = useState<UserProfile[]>(() => {
    const cached = sessionStorage.getItem('scotty_networking_discover')
    return cached ? JSON.parse(cached) : []
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchNetworkingData = useCallback(async (includeDiscover = true) => {
    const user = StorageUtil.getUser()
    if (!user?.id) return { error: 'No user session' }

    setLoading(true)
    setError(null)
    try {
      const fetchers = [
        fetch(apiUrl(`/api/networking/appointments/${user.id}`), { headers: authHeaders() })
      ]

      if (includeDiscover) {
        fetchers.push(fetch(apiUrl('/api/accounts/discover')))
      }

      const results = await Promise.all(fetchers)

      // Handle Appointments
      const apptData = await results[0].json()
      const returnedAppts = apptData.appointments || []
      setAppointments(returnedAppts)
      sessionStorage.setItem('scotty_networking_appointments', JSON.stringify(returnedAppts))

      // Handle Discover Users
      if (includeDiscover && results[1]) {
        const discoverData = await results[1].json()
        const allUsers: UserProfile[] = discoverData.users || []
        setDiscoverUsers(allUsers)
        sessionStorage.setItem('scotty_networking_discover', JSON.stringify(allUsers))

        // Return profile for the current user if found (for profile editor)
        const me = allUsers.find(u => u.username === user.username)
        return { me, appointments: returnedAppts }
      }

      return { appointments: returnedAppts }
    } catch (err) {
      const msg = 'Failed to fetch networking data'
      setError(msg)
      return { error: msg }
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    appointments,
    setAppointments,
    discoverUsers,
    loading,
    error,
    fetchNetworkingData
  }
}
