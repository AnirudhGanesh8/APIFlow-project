import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import { googleLoginUrl } from '../api/auth'
import { getApiErrorMessage } from '../api/errors'
import { useAuth } from '../context/useAuth'

export default function Login() {
  const { login } = useAuth(); const navigate = useNavigate(); const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' }); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault(); setError(''); setBusy(true)
    try { await login(form); const returnTo = new URLSearchParams(location.search).get('returnTo'); navigate(returnTo?.startsWith('/accept-invite?token=') ? returnTo : '/dashboard') } catch (err) { setError(getApiErrorMessage(err, 'Unable to log in.')) } finally { setBusy(false) }
  }
  return <AuthLayout title="Welcome back" subtitle="Sign in to your request workspace."><form onSubmit={submit} className="auth-form"><label>Email<input type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label><label>Password<input type="password" required value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>{error && <p className="error">{error}</p>}<button disabled={busy}>{busy ? 'Signing in...' : 'Sign in'}</button></form><a className="secondary-button" href={googleLoginUrl()}>Continue with Google</a><p className="form-footer"><Link to="/forgot-password">Forgot password?</Link> · <Link to={`/signup${location.search}`}>Create account</Link></p></AuthLayout>
}