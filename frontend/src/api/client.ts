import axios from 'axios';

export const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Inject auth headers on every request
api.interceptors.request.use((config) => {
  const token  = localStorage.getItem('biofabric_token');
  const stored = localStorage.getItem('biofabric_user');
  if (token && stored) {
    try {
      const user = JSON.parse(stored);
      config.headers['Authorization']  = `Bearer ${token}`;
      config.headers['X-User-Id']      = String(user.user_id);
      config.headers['X-User-Roles']   = (user.roles ?? []).join(',');
    } catch {
      // ignore parse errors
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Ошибка сервера';
    console.error('API Error:', message);
    if (error.response?.status === 401) {
      localStorage.removeItem('biofabric_token');
      localStorage.removeItem('biofabric_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
