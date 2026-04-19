import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),
  updateMe: (data) => api.put('/auth/me', data),
}

// Documents API
export const documentsAPI = {
  upload: (formData) => api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  list: (params = {}) => api.get('/documents', { params }),
  get: (id) => api.get(`/documents/${id}`),
  delete: (id) => api.delete(`/documents/${id}`),
  getChunks: (id, params = {}) => api.get(`/documents/${id}/chunks`, { params }),
  reprocess: (id) => api.post(`/documents/${id}/reprocess`),
}

// Queries API
export const queriesAPI = {
  askQuestion: (data) => api.post('/queries/qa', data),
  summarize: (data) => api.post('/queries/summarize', data),
  getHistory: (params = {}) => api.get('/queries/history', { params }),
  getResult: (sessionId) => api.get(`/queries/${sessionId}`),
  getMetrics: () => api.get('/queries/evaluation/metrics'),
}

// Analytics API
export const analyticsAPI = {
  getOverview: (days = 30) => api.get('/analytics/overview', { params: { days } }),
  getCost: (days = 30) => api.get('/analytics/cost', { params: { days } }),
  getModelPerformance: (days = 30) => api.get('/analytics/model-performance', { params: { days } }),
  getProcessing: (days = 30) => api.get('/analytics/processing', { params: { days } }),
  getQueryTimeline: (days = 30) => api.get('/analytics/query-timeline', { params: { days } }),
  getVoting: (days = 30) => api.get('/analytics/voting', { params: { days } }),
  getCitations: (days = 30) => api.get('/analytics/citations', { params: { days } }),
}

export default api
