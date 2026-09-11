import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { acceptMyInvite, declineMyInvite, listMyInvites } from '../api/workspaces'

export default function MyInvitations() {
  const navigate = useNavigate()
  const [invites, setInvites] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    listMyInvites().then(({ data }) => setInvites(data)).catch((err) => setError(getApiErrorMessage(err, 'Unable to load invitations.')))
  }, [])

  async function accept(inviteId) {
    setError('')
    try {
      const { data } = await acceptMyInvite(inviteId)
      navigate(`/workspaces/${data.id}/settings`)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to accept invitation.'))
    }
  }

  async function decline(inviteId) {
    setError('')
    try {
      await declineMyInvite(inviteId)
      setInvites((current) => current.filter((invite) => invite.id !== inviteId))
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to decline invitation.'))
    }
  }

  if (!error && invites.length === 0) return null

  return <section className="settings-section invitations-panel">
    <p className="eyebrow">MY INVITATIONS / {invites.length}</p>
    {error && <p className="error">{error}</p>}
    {invites.map((invite) => <div className="invitation-row" key={invite.id}>
      <div><strong>{invite.workspace_name}</strong><span>Invited by {invite.inviter_name} as {invite.role}</span></div>
      <div className="invitation-actions"><button className="compact-button" onClick={() => accept(invite.id)}>Accept</button><button className="secondary-button" onClick={() => decline(invite.id)}>Decline</button></div>
    </div>)}
  </section>
}