export function getApiErrorMessage(error, fallback) {
  if (!error?.response) {
    return 'The API server is unavailable. Start the backend and try again.'
  }

  const detail = error.response.data?.detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(' ')
  }

  return detail || fallback
}