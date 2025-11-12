import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const sitesAPI = {
  list: () => api.get('/sites'),
  get: (id) => api.get(`/sites/${id}`),
  create: (data) => api.post('/sites', data),
  update: (id, data) => api.put(`/sites/${id}`, data),
  delete: (id) => api.delete(`/sites/${id}`),
  poll: (id) => api.post(`/sites/${id}/poll`),
  getHistory: (id, limit = 50) => api.get(`/sites/${id}/history`, { params: { limit } }),
};

export const stateAPI = {
  getAll: () => api.get('/state'),
  get: (id) => api.get(`/state/${id}`),
  pause: () => api.post('/state/pause'),
  resume: () => api.post('/state/resume'),
  reload: () => api.post('/state/reload'),
};

export default api;
