import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/useAuth'

export default function AcceptInvite() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { isAuthenticated, loading } = useAuth()
  const token = params.get('token')

  useEffect(() => {
    if (loading) return
    if (!isAuthenticated) {
      navigate('/login?returnTo=%2Fdashboard', { replace: true })
      return
    }
    navigate('/dashboard', { replace: true, state: { inviteLinkOpened: Boolean(token) } })
  }, [isAuthenticated, loading, navigate, token])

  return <main className="page-center"><p className="muted">Taking you to your dashboard...</p></main>
}
