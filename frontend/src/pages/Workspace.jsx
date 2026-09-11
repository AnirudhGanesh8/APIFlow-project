import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { createCollection, deleteCollection, listCollections, renameCollection } from '../api/collections'
import { getWorkspace } from '../api/workspaces'
import AppNavigation from '../components/AppNavigation'
import { useAuth } from '../context/useAuth'

const roleRank = { viewer: 1, member: 2, admin: 3, owner: 4 }

export default function Workspace() {
  const { user } = useAuth()
  const { workspaceId } = useParams()
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState(null)
  const [collections, setCollections] = useState([])
  const [name, setName] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editingName, setEditingName] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getWorkspace(workspaceId), listCollections(workspaceId)])
      .then(([workspaceResponse, collectionResponse]) => {
        setWorkspace(workspaceResponse.data)
        setCollections(collectionResponse.data)
      })
      .catch((err) => {
        if (err.response?.status === 403 || err.response?.status === 404) navigate('/workspaces', { replace: true })
        else setError(getApiErrorMessage(err, 'Unable to load collections.'))
      })
      .finally(() => setLoading(false))
  }, [workspaceId, navigate])

  if (loading) return <main className="page-center"><p className="muted">Loading collections...</p></main>
  if (!workspace) return <main className="page-center"><p className="error">{error || 'Workspace unavailable.'}</p></main>

  const currentMember = workspace.members.find((member) => member.user_id === user.id)
  const canEdit = roleRank[currentMember?.role] >= roleRank.member
  const canDelete = roleRank[currentMember?.role] >= roleRank.admin

  async function createNewCollection(event) {
    event.preventDefault()
    if (!name.trim()) return
    setError(''); setSaving(true)
    try {
      const { data } = await createCollection(workspaceId, { name })
      setCollections((items) => [...items, data]); setName('')
    } catch (err) { setError(getApiErrorMessage(err, 'Unable to create collection.')) } finally { setSaving(false) }
  }

  function beginRename(item) { setEditingId(item.id); setEditingName(item.name); setError('') }

  async function saveRename(collectionId) {
    if (!editingName.trim()) return
    setError(''); setSaving(true)
    try {
      const { data } = await renameCollection(collectionId, { name: editingName })
      setCollections((items) => items.map((item) => item.id === collectionId ? data : item)); setEditingId(null)
    } catch (err) { setError(getApiErrorMessage(err, 'Unable to rename collection.')) } finally { setSaving(false) }
  }

  async function removeCollection(item) {
    if (!window.confirm(`Delete the ${item.name} collection?`)) return
    setError(''); setSaving(true)
    try {
      await deleteCollection(item.id)
      setCollections((items) => items.filter((current) => current.id !== item.id))
    } catch (err) { setError(getApiErrorMessage(err, 'Unable to delete collection.')) } finally { setSaving(false) }
  }

  return <main className="workspace-shell">
    <header className="app-header">
      <div className="header-title"><AppNavigation /><div><p className="eyebrow">APIFLOW / WORKSPACE</p><h1>{workspace.name}</h1></div></div>
      <div className="header-actions"><Link className="compact-button button-link" to={`/workspaces/${workspaceId}/settings`}>Settings</Link><button className="compact-button" onClick={() => navigate('/workspaces')}>All workspaces</button></div>
    </header>
    <section className="workspace-content">
      <div className="section-heading"><div><p className="eyebrow">COLLECTIONS / {collections.length}</p><p className="muted">Organize the requests for this workspace.</p></div>{canEdit && <form className="collection-create" onSubmit={createNewCollection}><input aria-label="Collection name" placeholder="New collection name" value={name} onChange={(event) => setName(event.target.value)} /><button className="compact-button" disabled={saving}>New collection</button></form>}</div>
      {error && <p className="error">{error}</p>}
      {collections.length === 0 ? <div className="empty-state"><h2>No collections yet.</h2><p className="muted">{canEdit ? 'Create a collection to give your API requests a home.' : 'A workspace member has not created a collection yet.'}</p></div> : <div className="collection-list">{collections.map((item) => <div className="collection-row" key={item.id}>
        {editingId === item.id ? <div className="collection-edit"><input autoFocus aria-label={`Rename ${item.name}`} value={editingName} onChange={(event) => setEditingName(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') saveRename(item.id); if (event.key === 'Escape') setEditingId(null) }} /><button className="compact-button" onClick={() => saveRename(item.id)} disabled={saving}>Save</button><button className="secondary-button compact-button" onClick={() => setEditingId(null)}>Cancel</button></div> : <><Link className="collection-link" to={`/collections/${item.id}`}><span className="collection-mark">C</span><span><strong>{item.name}</strong><small>Created {new Date(item.created_at).toLocaleDateString()}</small></span></Link>{canEdit && <button className="secondary-button compact-button" onClick={() => beginRename(item)}>Rename</button>}{canDelete && <button className="danger-button compact-button" onClick={() => removeCollection(item)} disabled={saving}>Delete</button>}</>}
      </div>)}</div>}
    </section>
  </main>
}