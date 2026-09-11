import { useState } from 'react'
import AuthLayout from '../components/AuthLayout'
import { forgotPassword } from '../api/auth'
import { getApiErrorMessage } from '../api/errors'

export default function ForgotPassword() {
  const [email, setEmail] = useState(''); const [message, setMessage] = useState(''); const [error, setError] = useState('')
  async function submit(event) { event.preventDefault(); setError(''); try { const { data } = await forgotPassword({ email }); setMessage(data.message) } catch (err) { setError(getApiErrorMessage(err, 'Unable to send reset link.')) } }
  return <AuthLayout title="Reset your password" subtitle="We will send a reset link if the account exists."><form onSubmit={submit} className="auth-form"><label>Email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>{message && <p className="success">{message}</p>}{error && <p className="error">{error}</p>}<button>Send reset link</button></form></AuthLayout>
}