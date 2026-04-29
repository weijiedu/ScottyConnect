import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import StorageUtil from './StorageUtil'

type Props = {
  children: ReactNode
}

/**
 * Redirects to /login when no JWT is present. Use for routes that require an authenticated user.
 * Preserves the attempted path in location state as `from` for post-login redirect.
 */
export default function ProtectedRoute({ children }: Props) {
  const location = useLocation()

  if (!StorageUtil.getToken()) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <>{children}</>
}
