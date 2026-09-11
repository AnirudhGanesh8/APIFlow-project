import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { acceptInvite } from '../api/workspaces'
import { getApiErrorMessage } from '../api/errors'

export default function AcceptInvite() {
  const [params] = useSearchParams(); const navigate = useNavigate(); const [error, setError] = useState(''); const [loading, setLoading] = useState(true)
  useEffect(() => { const token = params.get('token'); if (!token) { setError('This invite link is missing its token.'); setLoading(false); return } acceptInvite(token).then(({ data }) => navigate(`/workspaces/${data.id}/settings`, { replace: true })).catch((err) => { setError(getApiErrorMessage(err, 'Unable to accept invite.')); setLoading(false) }) }, [navigate, params])
  return <main className="page-center"><section className="auth-panel">{loading ? <p className="muted">Accepting workspace invite...</p> : <><p className="error">{error}</p><Link className="back-link" to="/workspaces">Return to workspaces</Link></>}</section></main>
}