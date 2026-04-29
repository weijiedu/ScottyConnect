import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import '../styles/Auth.css'
import StorageUtil from '../common/StorageUtil'
import { apiUrl } from '../services/Config'
export default function RegisterPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [role, setRole] = useState('STUDENT')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)

  function validate(): boolean {
    const errs: Record<string, string> = {}
    if (!username.trim()) errs.username = 'Username is required.'
    if (!email.trim()) errs.email = 'Email is required.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      errs.email = 'Enter a valid email address.'
    if (!password) errs.password = 'Password is required.'
    else if (password.length < 6) errs.password = 'Password must be at least 6 characters.'
    if (password !== confirmPassword) errs.confirmPassword = 'Passwords do not match.'
    setFieldErrors(errs)
    return Object.keys(errs).length === 0
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (!validate()) return

    setLoading(true)
    try {
      const res = await fetch(apiUrl('/api/accounts/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          email: email.trim(),
          password,
          confirm_password: confirmPassword,
          role,
        }),
      })
      const data = await res.json()

      if (!res.ok) {
        if (data.errors) {
          const msgs = data.errors.map((err: { msg: string }) => err.msg)
          setError(msgs.join(' '))
        } else {
          setError(data.message || 'Registration failed.')
        }
        return
      }

      StorageUtil.setUser(data.user.username, data.user.email, data.user.id)
      navigate('/verify')
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
          <h1>ScottyConnect</h1>
          <p>Create your account</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {error && <div className="auth-error">{error}</div>}

          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              placeholder="Choose a username"
              autoComplete="username"
              className={fieldErrors.username ? 'input-error' : ''}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            {fieldErrors.username && <p className="field-error">{fieldErrors.username}</p>}
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="you@andrew.cmu.edu"
              autoComplete="email"
              className={fieldErrors.email ? 'input-error' : ''}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {fieldErrors.email && <p className="field-error">{fieldErrors.email}</p>}
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="At least 6 characters"
              autoComplete="new-password"
              className={fieldErrors.password ? 'input-error' : ''}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {fieldErrors.password && <p className="field-error">{fieldErrors.password}</p>}
          </div>

          <div className="form-group">
            <label htmlFor="confirm-password">Confirm Password</label>
            <input
              id="confirm-password"
              type="password"
              placeholder="Re-enter your password"
              autoComplete="new-password"
              className={fieldErrors.confirmPassword ? 'input-error' : ''}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            {fieldErrors.confirmPassword && (
              <p className="field-error">{fieldErrors.confirmPassword}</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="role">Role</label>
            <select
              id="role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="STUDENT">Student</option>
              <option value="ALUMNI">Alumni</option>
            </select>
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <div className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  )
}
