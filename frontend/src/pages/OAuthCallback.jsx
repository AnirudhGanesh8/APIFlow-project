import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { setAccessToken } from '../api/client'
import { useAuth } from '../context/useAuth'

export default function OAuthCallback() {
  const { loadCurrentUser } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  useEffect(() => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get('access_token')
    if (!token) {
      setError('Google sign-in did not return an access token.')
      return
    }

    setAccessToken(token)
    loadCurrentUser()
      .then(() => navigate('/dashboard', { replace: true }))
      .catch(() => setError('Google sign-in completed, but the API session could not be loaded.'))
  }, [loadCurrentUser, navigate])

  return error
    ? <main className="page-center"><section className="auth-panel"><p className="error">{error}</p><a className="back-link" href="/login">Return to login</a></section></main>
    : <main className="page-center"><p className="muted">Completing Google sign-in...</p></main>
}
