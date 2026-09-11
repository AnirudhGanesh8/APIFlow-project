import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

export default function AppNavigation() {
  const navigate = useNavigate()
  const location = useLocation()
  const [historyBounds, setHistoryBounds] = useState({ canGoBack: false, canGoForward: false })

  useEffect(() => {
    const navigation = window.navigation
    if (navigation?.currentEntry) {
      const currentIndex = navigation.currentEntry.index ?? 0
      const entryCount = navigation.entries().length
      setHistoryBounds({ canGoBack: currentIndex > 0, canGoForward: currentIndex < entryCount - 1 })
      return
    }

    const currentIndex = window.history.state?.idx ?? 0
    setHistoryBounds({ canGoBack: currentIndex > 0, canGoForward: false })
  }, [location.key])

  return <nav className="app-navigation" aria-label="App navigation">
    <button type="button" className="nav-icon-button" onClick={() => navigate(-1)} disabled={!historyBounds.canGoBack} aria-label="Go back" title="Go back">←</button>
    <button type="button" className="nav-icon-button" onClick={() => navigate('/dashboard')} aria-label="Home" title="Home">⌂</button>
    <button type="button" className="nav-icon-button" onClick={() => navigate(1)} disabled={!historyBounds.canGoForward} aria-label="Go forward" title="Go forward">→</button>
  </nav>
}