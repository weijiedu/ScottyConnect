import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import '../styles/Auth.css'
import StorageUtil from '../common/StorageUtil'
import { apiUrl } from '../services/Config'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const loginState = location.state as { message?: string; from?: string } | null
  const successMessage = loginState?.message
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')

    if (!username.trim() || !password.trim()) {
      setError('Please enter both username and password.')
      return
    }

    setLoading(true)
    try {
      const res = await fetch(apiUrl('/api/accounts/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password: password.trim() }),
      })
      
      const data = await res.json()

      if (data.code === 403) {
        StorageUtil.setUser(data.user.username, data.user.email, data.user.id)
        navigate('/verify')
        return
      }

      if (!res.ok) {
        setError(data.message || 'Login failed. Please try again.')
        return
      }

      StorageUtil.setUser(data.user.username, data.user.email, data.user.id)
      StorageUtil.setToken(data.token)
      navigate(loginState?.from || '/mainpage')
    } catch {
      setError('Unable to connect to the server.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-icon">
              <img
                src="/scotty_connect_square.png"
                alt="ScottyConnect logo"
              />
          </div>
          <h1>Scotty Connect</h1>
          <p>Sign in to your account</p>

        </div>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {successMessage && <div className="auth-success">{successMessage}</div>}
          {error && <div className="auth-error">{error}</div>}

          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              placeholder="Enter your username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="Enter your password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="auth-footer">
          Don't have an account? <Link to="/register">Sign up</Link>
        </div>

      </div>
    </div>
  )
}
