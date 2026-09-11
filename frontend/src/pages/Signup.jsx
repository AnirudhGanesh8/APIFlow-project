import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import { getApiErrorMessage } from '../api/errors'
import { useAuth } from '../context/useAuth'

export default function Signup() {
  const { signup } = useAuth(); const navigate = useNavigate(); const location = useLocation()
  const [form, setForm] = useState({ name: '', email: '', password: '' }); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault(); setError(''); setBusy(true)
    try { await signup(form); const returnTo = new URLSearchParams(location.search).get('returnTo'); navigate(returnTo?.startsWith('/accept-invite?token=') ? returnTo : '/dashboard') } catch (err) { setError(getApiErrorMessage(err, 'Unable to create account.')) } finally { setBusy(false) }
  }
  return <AuthLayout title="Create your account" subtitle="Start building a trustworthy API workspace."><form onSubmit={submit} className="auth-form"><label>Name<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label>Email<input type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label><label>Password<input type="password" minLength="8" required value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>{error && <p className="error">{error}</p>}<button disabled={busy}>{busy ? 'Creating...' : 'Create account'}</button></form></AuthLayout>
}