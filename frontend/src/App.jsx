import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import { useAuth } from './context/useAuth'
import Dashboard from './pages/Dashboard'
import ForgotPassword from './pages/ForgotPassword'
import Login from './pages/Login'
import OAuthCallback from './pages/OAuthCallback'
import ResetPassword from './pages/ResetPassword'
import Signup from './pages/Signup'
import AcceptInvite from './pages/AcceptInvite'
import WorkspaceList from './pages/WorkspaceList'
import WorkspaceSettings from './pages/WorkspaceSettings'

function PublicRedirect() {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <main className="page-center">Loading APIFlow...</main>
  return <Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />
}

export default function App() {
  return <Routes><Route path="/" element={<PublicRedirect />} /><Route path="/login" element={<Login />} /><Route path="/signup" element={<Signup />} /><Route path="/forgot-password" element={<ForgotPassword />} /><Route path="/reset-password" element={<ResetPassword />} /><Route path="/oauth/callback" element={<OAuthCallback />} /><Route element={<ProtectedRoute />}><Route path="/dashboard" element={<Dashboard />} /><Route path="/workspaces" element={<WorkspaceList />} /><Route path="/workspaces/:workspaceId/settings" element={<WorkspaceSettings />} /><Route path="/accept-invite" element={<AcceptInvite />} /></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes>
}
