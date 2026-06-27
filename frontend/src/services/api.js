import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('chronos_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('chronos_token');
      localStorage.removeItem('chronos_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: () => api.post('/auth/login'),
  callback: (code) => api.get(`/auth/callback?code=${code}`),
  demo: () => api.post('/auth/demo'),
};

export const tasksAPI = {
  create: (input) => api.post('/tasks/create', { input }),
  list: (status) => api.get('/tasks', { params: status ? { status } : {} }),
  get: (id) => api.get(`/tasks/${id}`),
  complete: (id) => api.put(`/tasks/${id}/complete`),
};

export const dashboardAPI = {
  get: () => api.get('/dashboard'),
};

export const chatAPI = {
  send: (message, history = []) => api.post('/chat', { message, history }),
};

export default api;
