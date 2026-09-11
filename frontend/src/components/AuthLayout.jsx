import { Link } from 'react-router-dom'

export default function AuthLayout({ title, subtitle, children }) {
  return <main className="page-center"><section className="auth-panel"><p className="eyebrow">APIFLOW</p><h1>{title}</h1><p className="muted">{subtitle}</p>{children}<Link className="back-link" to="/login">Back to login</Link></section></main>
}