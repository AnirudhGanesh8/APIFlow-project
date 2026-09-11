import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  withCredentials: true,
})

let accessToken = null
let refreshPromise = null

export function setAccessToken(token) { accessToken = token }
export function clearAccessToken() { accessToken = null }

export async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = client.post('/auth/refresh', {}).then(({ data }) => {
      setAccessToken(data.access_token)
      return data
    }).finally(() => { refreshPromise = null })
  }
  return refreshPromise
}

client.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

client.interceptors.response.use((response) => response, async (error) => {
  const originalRequest = error.config
  if (error.response?.status !== 401 || originalRequest?._retry || originalRequest?.url?.includes('/auth/refresh')) return Promise.reject(error)
  originalRequest._retry = true
  try {
    await refreshAccessToken()
    return client(originalRequest)
  } catch (refreshError) {
    clearAccessToken()
    return Promise.reject(refreshError)
  }
})

export default client