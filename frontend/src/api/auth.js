import client from './client'

export const signup = (payload) => client.post('/auth/signup', payload)
export const login = (payload) => client.post('/auth/login', payload)
export const refresh = () => client.post('/auth/refresh', {})
export const logout = () => client.post('/auth/logout')
export const forgotPassword = (payload) => client.post('/auth/forgot-password', payload)
export const resetPassword = (payload) => client.post('/auth/reset-password', payload)
export const getMe = () => client.get('/auth/me')

export function googleLoginUrl() {
  return `${import.meta.env.VITE_API_URL || '/api/v1'}/auth/google/login`
}