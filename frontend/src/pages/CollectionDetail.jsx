import { Link, useNavigate, useParams } from 'react-router-dom'
import AppNavigation from '../components/AppNavigation'

export default function CollectionDetail() {
  const { collectionId } = useParams()
  const navigate = useNavigate()

  return <main className="workspace-shell"><header className="app-header"><div className="header-title"><AppNavigation /><div><p className="eyebrow">APIFLOW / COLLECTION</p><h1>Collection</h1></div></div><button className="compact-button" onClick={() => navigate(-1)}>Back to workspace</button></header><section className="workspace-content"><div className="placeholder-panel"><p className="eyebrow">COLLECTION {collectionId.slice(0, 8)}</p><h2>Requests will live here.</h2><p className="muted">The request builder is the next module. This collection is ready for it.</p><Link className="back-link" to="/workspaces">Return to workspaces</Link></div></section></main>
}