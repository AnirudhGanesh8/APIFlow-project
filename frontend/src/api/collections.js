import client from './client'

export const listCollections = (workspaceId) => client.get(`/workspaces/${workspaceId}/collections`)
export const createCollection = (workspaceId, payload) => client.post(`/workspaces/${workspaceId}/collections`, payload)
export const getCollection = (collectionId) => client.get(`/collections/${collectionId}`)
export const renameCollection = (collectionId, payload) => client.patch(`/collections/${collectionId}`, payload)
export const deleteCollection = (collectionId) => client.delete(`/collections/${collectionId}`)