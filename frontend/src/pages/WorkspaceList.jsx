import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { createWorkspace, listWorkspaces } from '../api/workspaces'
import { useAuth } from '../context/useAuth'

export default function WorkspaceList() {
  const { logout } = useAuth(); const navigate = useNavigate()
  const [workspaces, setWorkspaces] = useState([]); const [name, setName] = useState(''); const [showCreate, setShowCreate] = useState(false); const [loading, setLoading] = useState(true); const [error, setError] = useState('')

  const load = useCallback(async () => { try { const { data } = await listWorkspaces(); setWorkspaces(data) } catch (err) { if (err.response?.status === 403) navigate('/login', { replace: true }); else setError(getApiErrorMessage(err, 'Unable to load workspaces.')) } finally { setLoading(false) } }, [navigate])
  useEffect(() => { load() }, [load])

  async function submit(event) { event.preventDefault(); setError(''); try { const { data } = await createWorkspace({ name }); navigate(`/workspaces/${data.id}/settings`) } catch (err) { setError(getApiErrorMessage(err, 'Unable to create workspace.')) } }

  return <main className="workspace-shell"><header className="app-header"><div><p className="eyebrow">APIFLOW / WORKSPACES</p><h1>Your workspaces</h1></div><button className="compact-button" onClick={logout}>Log out</button></header><section className="workspace-content"><div className="section-heading"><p className="muted">Projects you belong to.</p><button className="compact-button" onClick={() => setShowCreate(true)}>+ New workspace</button></div>{error && <p className="error">{error}</p>}{loading ? <p className="muted">Loading workspaces...</p> : workspaces.length === 0 ? <div className="empty-state"><h2>No workspaces yet.</h2><p className="muted">Create the first workspace for your API team.</p></div> : <div className="workspace-grid">{workspaces.map((workspace) => <Link className="workspace-card" key={workspace.id} to={`/workspaces/${workspace.id}/settings`}><span className="workspace-mark">W</span><h2>{workspace.name}</h2><p>{workspace.members.length} member{workspace.members.length === 1 ? '' : 's'}</p></Link>)}</div>}</section>{showCreate && <div className="modal-backdrop" onMouseDown={() => setShowCreate(false)}><section className="modal" onMouseDown={(event) => event.stopPropagation()}><p className="eyebrow">NEW WORKSPACE</p><h2>Name your workspace</h2><form onSubmit={submit} className="auth-form"><label>Workspace name<input autoFocus required value={name} onChange={(event) => setName(event.target.value)} /></label><div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setShowCreate(false)}>Cancel</button><button type="submit">Create workspace</button></div></form></section></div>}</main>
}