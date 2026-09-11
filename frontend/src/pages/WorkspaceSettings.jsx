import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import AppNavigation from '../components/AppNavigation'
import { changeMemberRole, createInvite, deleteWorkspace, getWorkspace, listPendingInvites, renameWorkspace, revokeInvite } from '../api/workspaces'
import { useAuth } from '../context/useAuth'

function useAutoDismissSuccess(success, clearSuccess) {
  useEffect(() => {
    if (!success) return undefined
    const timeout = window.setTimeout(() => clearSuccess(), 3500)
    return () => window.clearTimeout(timeout)
  }, [success, clearSuccess])
}

function SectionMessage({ message }) {
  if (!message?.error && !message?.success) return null
  return <p className={message.error ? 'error' : 'success'}>{message.error || message.success}</p>
}

function truncateInviteLink(link) {
  if (link.length <= 64) return link
  const marker = '?token='
  const markerIndex = link.indexOf(marker)
  if (markerIndex === -1) return `${link.slice(0, 28)}...${link.slice(-12)}`
  const tokenStart = markerIndex + marker.length
  const token = link.slice(tokenStart)
  return `${link.slice(0, tokenStart)}${token.slice(0, 20)}...${token.slice(-8)}`
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand('copy')
  textarea.remove()
  if (!copied) throw new Error('Clipboard access is unavailable.')
}

export default function WorkspaceSettings() {
  const { user } = useAuth()
  const { workspaceId } = useParams()
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState(null)
  const [name, setName] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [inviteLink, setInviteLink] = useState('')
  const [pendingInvites, setPendingInvites] = useState([])
  const [pendingError, setPendingError] = useState('')
  const [copyMessage, setCopyMessage] = useState({ error: '', success: '' })
  const [renameMessage, setRenameMessage] = useState({ error: '', success: '' })
  const [deleteError, setDeleteError] = useState('')
  const [inviteMessage, setInviteMessage] = useState({ error: '', success: '' })
  const [memberMessage, setMemberMessage] = useState({ error: '', success: '' })

  useAutoDismissSuccess(renameMessage.success, () => setRenameMessage((message) => ({ ...message, success: '' })))
  useAutoDismissSuccess(inviteMessage.success, () => setInviteMessage((message) => ({ ...message, success: '' })))
  useAutoDismissSuccess(memberMessage.success, () => setMemberMessage((message) => ({ ...message, success: '' })))
  useAutoDismissSuccess(copyMessage.success, () => setCopyMessage((message) => ({ ...message, success: '' })))

  useEffect(() => {
    getWorkspace(workspaceId)
      .then(({ data }) => {
        setWorkspace(data)
        setName(data.name)
        return listPendingInvites(workspaceId)
      })
      .then(({ data }) => setPendingInvites(data))
      .catch((err) => {
        if (err.response?.status === 403) navigate('/workspaces', { replace: true })
        else setMemberMessage({ error: getApiErrorMessage(err, 'Unable to load workspace.'), success: '' })
      })
  }, [workspaceId, navigate])

  async function rename(event) {
    event.preventDefault()
    setRenameMessage({ error: '', success: '' })
    try {
      const { data } = await renameWorkspace(workspaceId, { name })
      setWorkspace(data)
      setRenameMessage({ error: '', success: 'Workspace renamed.' })
    } catch (err) {
      setRenameMessage({ error: getApiErrorMessage(err, 'Unable to rename workspace.'), success: '' })
    }
  }

  async function remove() {
    if (!window.confirm('Delete this workspace permanently?')) return
    setDeleteError('')
    try {
      await deleteWorkspace(workspaceId)
      navigate('/workspaces', { replace: true })
    } catch (err) {
      setDeleteError(getApiErrorMessage(err, 'Unable to delete workspace.'))
    }
  }

  async function invite(event) {
    event.preventDefault()
    setInviteMessage({ error: '', success: '' })
    try {
      const { data } = await createInvite(workspaceId, { email: inviteEmail, role: inviteRole })
      setInviteLink(data.invite.invite_link)
      setPendingInvites((invites) => [data.invite, ...invites])
      setInviteMessage({
        error: '',
        success: data.email_sent
          ? 'Invite sent and email sent.'
          : "Invite created, but the email couldn't be sent. Share the link manually.",
      })
      setCopyMessage({ error: '', success: '' })
    } catch (err) {
      setInviteMessage({ error: getApiErrorMessage(err, 'Unable to create invite.'), success: '' })
    }
  }

  async function revokePendingInvite(inviteId) {
    if (!window.confirm('Revoke this invite?')) return
    setPendingError('')
    try {
      await revokeInvite(workspaceId, inviteId)
      setPendingInvites((invites) => invites.filter((invite) => invite.id !== inviteId))
    } catch (err) {
      setPendingError(getApiErrorMessage(err, 'Unable to revoke invite.'))
    }
  }

  async function copyInviteLink() {
    setCopyMessage({ error: '', success: '' })
    try {
      await copyText(inviteLink)
      setCopyMessage({ error: '', success: 'Copied!' })
    } catch {
      setCopyMessage({ error: 'Copy failed. Please copy the invite link manually.', success: '' })
    }
  }

  async function roleChange(userId, role) {
    setMemberMessage({ error: '', success: '' })
    try {
      const { data } = await changeMemberRole(workspaceId, userId, { role })
      setWorkspace(data)
      setMemberMessage({ error: '', success: 'Member role updated.' })
    } catch (err) {
      setMemberMessage({ error: getApiErrorMessage(err, 'Unable to update member role.'), success: '' })
    }
  }

  if (!workspace) return <main className="page-center"><p className="muted">Loading workspace...</p></main>

  const currentMember = workspace.members.find((member) => member.user_id === user.id)
  const canManage = currentMember?.role === 'owner' || currentMember?.role === 'admin'
  const isOwner = currentMember?.role === 'owner'

  return <main className="workspace-shell">
    <header className="app-header">
      <div className="header-title"><AppNavigation /><div><p className="eyebrow">APIFLOW / WORKSPACE SETTINGS</p><h1>{workspace.name}</h1></div></div>
      <button className="compact-button" onClick={() => navigate('/workspaces')}>All workspaces</button>
    </header>
    <section className="workspace-content">
      <section className="settings-section">
        <p className="eyebrow">IDENTITY</p>
        <SectionMessage message={renameMessage} />
        <form onSubmit={rename} className="inline-form">
          <input value={name} onChange={(event) => setName(event.target.value)} />
          <button className="compact-button">Save name</button>
        </form>
        {isOwner && <>
          {deleteError && <p className="error">{deleteError}</p>}
          <button className="danger-button" onClick={remove}>Delete workspace</button>
        </>}
      </section>
      {canManage && <section className="settings-section">
        <p className="eyebrow">INVITE MEMBER</p>
        <SectionMessage message={inviteMessage} />
        <form onSubmit={invite} className="invite-form">
          <input type="email" required placeholder="teammate@example.com" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} />
          <select value={inviteRole} onChange={(event) => setInviteRole(event.target.value)}>
            <option value="member">Member</option>
            <option value="viewer">Viewer</option>
            <option value="admin">Admin</option>
          </select>
          <button className="compact-button">Create invite</button>
        </form>
        {inviteLink && <div className="invite-result"><span title={inviteLink}>{truncateInviteLink(inviteLink)}</span><div className="invite-copy"><button type="button" className="compact-button" onClick={copyInviteLink}>{copyMessage.success ? 'Copied!' : 'Copy'}</button>{copyMessage.error && <p className="error">{copyMessage.error}</p>}</div></div>}
        <div className="pending-invites">
          <p className="eyebrow">INVITATIONS / {pendingInvites.length}</p>
          {pendingError && <p className="error">{pendingError}</p>}
          {pendingInvites.length === 0 ? <p className="muted">No invitations yet.</p> : pendingInvites.map((invite) => <div className="pending-invite" key={invite.id}>
            <strong className="invite-email">{invite.email}</strong>
            <span className="invite-role">{invite.role}</span>
            <span className={`status-badge status-${invite.status}`}>{invite.status}</span>
            <span className="invite-expiry">{invite.status === 'pending' ? `Expires ${new Date(invite.expires_at).toLocaleDateString()}` : ''}</span>
            {invite.status === 'pending' && <button type="button" className="secondary-button" onClick={() => revokePendingInvite(invite.id)}>Revoke</button>}
          </div>)}
        </div>
      </section>}
      <section className="settings-section">
        <p className="eyebrow">MEMBERS / {workspace.members.length}</p>
        <SectionMessage message={memberMessage} />
        <div className="member-list">
          {workspace.members.map((member) => <div className="member-row" key={member.id}>
            <div><strong>{member.name}</strong><span>{member.email}</span></div>
            {member.role === 'owner' || member.user_id === user.id ? <span className="role-label">{member.user_id === user.id ? `You - ${member.role}` : 'Owner'}</span> : canManage ? <select value={member.role} onChange={(event) => roleChange(member.user_id, event.target.value)}>
              <option value="member">Member</option><option value="viewer">Viewer</option><option value="admin">Admin</option>
            </select> : <span className="role-label">{member.role}</span>}
          </div>)}
        </div>
      </section>
    </section>
  </main>
}
