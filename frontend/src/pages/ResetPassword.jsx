import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import { resetPassword } from '../api/auth'
import { getApiErrorMessage } from '../api/errors'

export default function ResetPassword() {
  const [params] = useSearchParams(); const [password, setPassword] = useState(''); const [message, setMessage] = useState(''); const [error, setError] = useState('')
  async function submit(event) { event.preventDefault(); setError(''); try { const { data } = await resetPassword({ token: params.get('token') || '', new_password: password }); setMessage(data.message) } catch (err) { setError(getApiErrorMessage(err, 'Unable to reset password.')) } }
  return <AuthLayout title="Choose a new password" subtitle="Use the secure link from your email."><form onSubmit={submit} className="auth-form"><label>New password<input type="password" minLength="8" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>{message && <p className="success">{message} <Link to="/login">Sign in</Link></p>}{error && <p className="error">{error}</p>}<button>Reset password</button></form></AuthLayout>
}