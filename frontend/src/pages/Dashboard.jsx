import { Link } from 'react-router-dom'
import AppNavigation from '../components/AppNavigation'
import MyInvitations from '../components/MyInvitations'
import { useAuth } from '../context/useAuth'

export default function Dashboard() {
  const { user, logout } = useAuth()
  return <main className="dashboard"><header><div className="header-title"><AppNavigation /><div><p className="eyebrow">APIFLOW</p><h1>Your workspace</h1></div></div><div className="header-actions"><Link className="compact-button" to="/workspaces">Workspaces</Link><button className="compact-button" onClick={logout}>Log out</button></div></header><section className="welcome"><p className="eyebrow">AUTHENTICATED</p><h2>Hello, {user.name}.</h2><p className="muted">Your APIFlow foundation is ready for the next module.</p><p className="email">{user.email}</p></section><MyInvitations /></main>
}