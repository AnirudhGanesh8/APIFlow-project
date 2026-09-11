import { createContext, useCallback, useEffect, useState } from 'react'
import * as authApi from '../api/auth'
import { clearAccessToken, refreshAccessToken, setAccessToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    refreshAccessToken().then((data) => setUser(data.user)).catch(() => clearAccessToken()).finally(() => setLoading(false))
  }, [])

  async function authenticate(request) {
    const { data } = await request
    setAccessToken(data.access_token)
    setUser(data.user)
  }

  const loadCurrentUser = useCallback(async () => {
    const { data } = await authApi.getMe()
    setUser(data)
  }, [])

  async function logout() {
    try { await authApi.logout() } finally { clearAccessToken(); setUser(null) }
  }

  const value = {
    user,
    loading,
    isAuthenticated: Boolean(user),
    signup: (payload) => authenticate(authApi.signup(payload)),
    login: (payload) => authenticate(authApi.login(payload)),
    loadCurrentUser,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export { AuthContext }