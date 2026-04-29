import { useRef, useState, type ClipboardEvent, type SubmitEvent, type KeyboardEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import '../styles/Auth.css'
import StorageUtil from '../common/StorageUtil'
import { apiUrl } from '../services/Config'

// Verification code length
const CODE_LEN = 6

export default function VerificationPage() {
  const navigate = useNavigate()
  const pending = StorageUtil.getUser()
  const verifyEmail = pending.email

  const [digits, setDigits] = useState<string[]>(() => Array(CODE_LEN).fill(''))
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const inputsRef = useRef<(HTMLInputElement | null)[]>([])

  const code = digits.join('')

  function focusCell(i: number) {
    inputsRef.current[i]?.focus()
    inputsRef.current[i]?.select()
  }

  function applyPastedDigits(text: string) {
    const only = text.replace(/\D/g, '').slice(0, CODE_LEN)
    if (!only) return
    setDigits((prev) => {
      const next = [...prev]
      for (let i = 0; i < CODE_LEN; i++) next[i] = only[i] ?? ''
      return next
    })
    focusCell(Math.min(only.length, CODE_LEN) - 1)
  }

  function handleDigitChange(index: number, value: string) {
    const raw = value.replace(/\D/g, '')
    if (!raw) {
      setDigits((prev) => {
        const next = [...prev]
        next[index] = ''
        return next
      })
      return
    }
    const ch = raw.slice(-1)
    setDigits((prev) => {
      const next = [...prev]
      next[index] = ch
      return next
    })
    if (index < CODE_LEN - 1) focusCell(index + 1)
  }

  function handleKeyDown(index: number, e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      e.preventDefault()
      setDigits((prev) => {
        const next = [...prev]
        next[index - 1] = ''
        return next
      })
      focusCell(index - 1)
      return
    }
    if (e.key === 'ArrowLeft' && index > 0) {
      e.preventDefault()
      focusCell(index - 1)
    }
    if (e.key === 'ArrowRight' && index < CODE_LEN - 1) {
      e.preventDefault()
      focusCell(index + 1)
    }
  }

  function handleOtpPaste(e: ClipboardEvent<HTMLInputElement>) {
    const text = e.clipboardData.getData('text')
    if (!/\d/.test(text)) return
    e.preventDefault()
    applyPastedDigits(text)
  }

  async function handleSubmit(e: SubmitEvent<HTMLFormElement>) {
    e.preventDefault()
    setError('')
    if (!pending) {
      setError('Return to sign in and try again so we know which account to verify.')
      return
    }
    if (code.length !== CODE_LEN) {
      setError('Enter the 6-digit code from your email.')
      return
    }

    setLoading(true)
    try {
      const res = await fetch(apiUrl('/api/accounts/verify'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: verifyEmail, code }),
      })
      const data = await res.json()

      if (!res.ok) {
        if (Array.isArray(data.errors)) {
          const msgs = data.errors.map((err: { msg: string }) => err.msg)
          setError(msgs.join(' '))
        } else {
          setError(data.message || 'Verification failed.')
        }
        return
      }

      StorageUtil.setUser(data.user.username, data.user.email, data.user.id)
      StorageUtil.setToken(data.token)
      navigate('/mainpage')
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
            <img src="/scotty_connect_square.png" alt="ScottyConnect logo" />
          </div>
          <h1>Verify your email</h1>
          <p>Enter the 6-digit code we sent to your inbox.</p>
          {verifyEmail ? (
            <p className="verify-email-display">
              Verifying <strong>{verifyEmail}</strong>
            </p>
          ) : (
            <p className="verify-email-display verify-email-missing">
              Sign in from the login page to open this screen with your account.
            </p>
          )}
        </div>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {error && <div className="auth-error">{error}</div>}

          <div className="form-group otp-group">
            <span className="otp-label" id="otp-label">
              Verification code
            </span>
            <div className="otp-row" role="group" aria-labelledby="otp-label">
              {digits.map((d, i) => (
                <input
                  key={i}
                  ref={(el) => {
                    inputsRef.current[i] = el
                  }}
                  type="text"
                  inputMode="numeric"
                  autoComplete={i === 0 ? 'one-time-code' : 'off'}
                  maxLength={1}
                  className="otp-cell"
                  value={d}
                  aria-label={`Digit ${i + 1} of ${CODE_LEN}`}
                  onChange={(e) => handleDigitChange(i, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(i, e)}
                  onPaste={handleOtpPaste}
                />
              ))}
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={loading || !verifyEmail}>
            {loading ? 'Verifying...' : 'Verify'}
          </button>
        </form>

        <div className="auth-footer">
          <Link to="/login">Back to sign in</Link>
        </div>
      </div>
    </div>
  )
}
