import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_HOST = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_BASE_URL = `${API_HOST}/api/v1`;

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token refresh state
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

// Process queued requests after token refresh
const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else {
      promise.resolve(token);
    }
  });
  failedQueue = [];
};

// Helper to get auth token from cookies
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  const match = document.cookie.match(/auth_token=([^;]+)/);
  return match ? match[1] : null;
}

// Helper to get refresh token from cookies
function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  const match = document.cookie.match(/refresh_token=([^;]+)/);
  return match ? match[1] : null;
}

// Helper to set auth cookies
function setAuthCookies(accessToken: string, refreshToken: string) {
  if (typeof window === 'undefined') return;
  const accessMaxAge = 30 * 60; // 30 minutes
  const refreshMaxAge = 7 * 24 * 60 * 60; // 7 days
  document.cookie = `auth_token=${accessToken}; path=/; max-age=${accessMaxAge}; SameSite=Lax`;
  document.cookie = `refresh_token=${refreshToken}; path=/; max-age=${refreshMaxAge}; SameSite=Lax`;
}

// Helper to clear auth cookies
function clearAuthCookies() {
  if (typeof window === 'undefined') return;
  document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
  document.cookie = 'refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
}

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling with token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Handle 401 errors with token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Skip refresh for login/register/refresh endpoints
      const skipRefreshUrls = ['/token', '/register', '/token/refresh'];
      if (skipRefreshUrls.some(url => originalRequest.url?.includes(url))) {
        return Promise.reject(error);
      }

      // Check if we have a refresh token
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        // No refresh token, redirect to login
        if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
          clearAuthCookies();
          window.location.href = '/login?error=' + encodeURIComponent('Session expired. Please login again.');
        }
        return Promise.reject(error);
      }

      // If already refreshing, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          if (token && originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${token}`;
          }
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Call the refresh endpoint
        const response = await axios.post(
          `${API_BASE_URL}/token/refresh`,
          null,
          { params: { refresh_token: refreshToken } }
        );

        const { access_token, refresh_token: newRefreshToken } = response.data;

        // Store new tokens
        setAuthCookies(access_token, newRefreshToken);

        // Update the failed request with new token
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        // Process queued requests
        processQueue(null, access_token);

        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        processQueue(refreshError as Error);
        clearAuthCookies();

        if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
          window.location.href = '/login?error=' + encodeURIComponent('Session expired. Please login again.');
        }

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Extract error message for non-401 errors
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
