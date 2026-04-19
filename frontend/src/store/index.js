import { create } from 'zustand'
import { authAPI, documentsAPI, queriesAPI } from '../api/client'

export const useAuthStore = create((set, get) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('token') || null,
  loading: false,
  error: null,

  login: async (email, password) => {
    set({ loading: true, error: null })
    try {
      const res = await authAPI.login({ email, password })
      const { user, access_token } = res.data
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify(user))
      set({ user, token: access_token, loading: false })
      return true
    } catch (err) {
      set({ error: err.response?.data?.error || 'Login failed', loading: false })
      return false
    }
  },

  register: async (email, password, fullName) => {
    set({ loading: true, error: null })
    try {
      const res = await authAPI.register({ email, password, full_name: fullName })
      const { user, access_token } = res.data
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify(user))
      set({ user, token: access_token, loading: false })
      return true
    } catch (err) {
      set({ error: err.response?.data?.error || 'Registration failed', loading: false })
      return false
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ user: null, token: null })
  },

  fetchUser: async () => {
    try {
      const res = await authAPI.getMe()
      set({ user: res.data.user })
      localStorage.setItem('user', JSON.stringify(res.data.user))
    } catch {
      get().logout()
    }
  },

  clearError: () => set({ error: null }),
}))

export const useDocumentsStore = create((set, get) => ({
  documents: [],
  currentDocument: null,
  chunks: [],
  loading: false,
  uploadProgress: 0,
  error: null,

  fetchDocuments: async (params = {}) => {
    set({ loading: true, error: null })
    try {
      const res = await documentsAPI.list(params)
      set({ documents: res.data.documents, loading: false })
      return res.data
    } catch (err) {
      set({ error: err.response?.data?.error || 'Failed to fetch documents', loading: false })
      return null
    }
  },

  uploadDocument: async (formData, onProgress) => {
    set({ loading: true, uploadProgress: 0, error: null })
    try {
      const res = await documentsAPI.upload(formData)
      set({ loading: false, uploadProgress: 100 })
      return res.data
    } catch (err) {
      set({ error: err.response?.data?.error || 'Upload failed', loading: false })
      return null
    }
  },

  getDocument: async (id) => {
    set({ loading: true, error: null })
    try {
      const res = await documentsAPI.get(id)
      set({ currentDocument: res.data.document, loading: false })
      return res.data.document
    } catch (err) {
      set({ error: err.response?.data?.error || 'Failed to get document', loading: false })
      return null
    }
  },

  deleteDocument: async (id) => {
    try {
      await documentsAPI.delete(id)
      set((state) => ({
        documents: state.documents.filter((d) => d.id !== id),
      }))
      return true
    } catch (err) {
      set({ error: err.response?.data?.error || 'Delete failed' })
      return false
    }
  },

  fetchChunks: async (docId, params = {}) => {
    try {
      const res = await documentsAPI.getChunks(docId, params)
      set({ chunks: res.data.chunks })
      return res.data
    } catch {
      return null
    }
  },

  clearError: () => set({ error: null }),
}))

export const useQAStore = create((set) => ({
  history: [],
  docHistory: [],     // Q&A sessions for the currently open document
  currentSession: null,
  currentResult: null,
  metrics: null,
  loading: false,
  error: null,

  askQuestion: async (documentId, question, topK = 5) => {
    set({ loading: true, error: null, currentResult: null })
    try {
      const res = await queriesAPI.askQuestion({ document_id: documentId, question, top_k: topK })
      set({ currentResult: res.data, loading: false })
      return res.data
    } catch (err) {
      set({ error: err.response?.data?.error || 'Query failed', loading: false })
      return null
    }
  },

  summarize: async (documentId, type = 'abstract') => {
    set({ loading: true, error: null, currentResult: null })
    try {
      const res = await queriesAPI.summarize({ document_id: documentId, type })
      set({ currentResult: res.data, loading: false })
      return res.data
    } catch (err) {
      set({ error: err.response?.data?.error || 'Summary failed', loading: false })
      return null
    }
  },

  fetchHistory: async (params = {}) => {
    set({ loading: true })
    try {
      const res = await queriesAPI.getHistory(params)
      if (params.document_id) {
        // Document-scoped history — merge into docHistory, avoid duplicates
        set((state) => {
          const existing = new Set(state.docHistory.map((s) => s.id))
          const fresh = res.data.sessions.filter((s) => !existing.has(s.id))
          return { docHistory: [...fresh, ...state.docHistory], loading: false }
        })
      } else {
        set({ history: res.data.sessions, loading: false })
      }
      return res.data
    } catch (err) {
      set({ error: err.response?.data?.error || 'Failed to fetch history', loading: false })
      return null
    }
  },

  clearDocHistory: () => set({ docHistory: [] }),

  fetchMetrics: async () => {
    try {
      const res = await queriesAPI.getMetrics()
      set({ metrics: res.data })
      return res.data
    } catch {
      return null
    }
  },
}))
