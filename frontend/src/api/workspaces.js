import client from './client'

export const listWorkspaces = () => client.get('/workspaces')
export const createWorkspace = (payload) => client.post('/workspaces', payload)
export const getWorkspace = (workspaceId) => client.get(`/workspaces/${workspaceId}`)
export const renameWorkspace = (workspaceId, payload) => client.patch(`/workspaces/${workspaceId}`, payload)
export const deleteWorkspace = (workspaceId) => client.delete(`/workspaces/${workspaceId}`)
export const createInvite = (workspaceId, payload) => client.post(`/workspaces/${workspaceId}/invites`, payload)
export const acceptInvite = (token) => client.post(`/workspaces/invites/${encodeURIComponent(token)}/accept`)
export const changeMemberRole = (workspaceId, userId, payload) => client.patch(`/workspaces/${workspaceId}/members/${userId}`, payload)