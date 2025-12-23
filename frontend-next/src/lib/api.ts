import axios, { AxiosError } from 'axios';

const API_HOST = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_BASE_URL = `${API_HOST}/api/v1`;

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper to get auth token from cookies
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  const match = document.cookie.match(/auth_token=([^;]+)/);
  return match ? match[1] : null;
}

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Redirect to login on 401 (but not if already on login page)
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
        window.location.href = '/login?error=' + encodeURIComponent('Session expired. Please login again.');
      }
    }

    // Extract error message
    if (error.response) {
      const data = error.response.data as Record<string, unknown>;
      const message = data?.detail || data?.message || data?.error || `Error (${error.response.status})`;
      return Promise.reject(new Error(String(message)));
    }
    return Promise.reject(new Error('Unable to connect to server'));
  }
);

export default api;
export { API_BASE_URL, API_HOST };
