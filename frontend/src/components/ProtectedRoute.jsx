import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/useAuth'

export default function ProtectedRoute() {
  const { loading, isAuthenticated } = useAuth()
  if (loading) return <main className="page-center">Restoring session...</main>
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />
}