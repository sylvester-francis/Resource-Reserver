/**
 * Api module.
 */

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

export const notificationsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get('/notifications', { params }),
  markRead: (id: number) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/mark-all-read'),
};

export const reservationsApi = {
  create: (payload: Record<string, unknown>) => api.post('/reservations', payload),
  createRecurring: (payload: Record<string, unknown>) =>
    api.post('/reservations/recurring', payload),
};

export const waitlistApi = {
  join: (payload: {
    resource_id: number;
    desired_start: string;
    desired_end: string;
    flexible_time?: boolean;
  }) => api.post('/waitlist', payload),
  list: (params?: Record<string, unknown>) =>
    api.get('/waitlist', { params }),
  get: (id: number) => api.get(`/waitlist/${id}`),
  leave: (id: number) => api.delete(`/waitlist/${id}`),
  accept: (id: number) => api.post(`/waitlist/${id}/accept`),
  getResourceWaitlist: (resourceId: number) =>
    api.get(`/waitlist/resource/${resourceId}`),
};

// Calendar Integration API
export const calendarApi = {
  getSubscriptionUrl: () => api.get('/calendar/subscription-url'),
  regenerateToken: () => api.post('/calendar/regenerate-token'),
  exportReservation: (reservationId: number) =>
    api.get(`/calendar/export/${reservationId}.ics`, { responseType: 'blob' }),
  getMyFeed: () => api.get('/calendar/my-feed', { responseType: 'blob' }),
};

// Analytics API
export const analyticsApi = {
  getDashboard: (params?: { days?: number }) =>
    api.get('/analytics/dashboard', { params }),
  getUtilization: (params?: { days?: number }) =>
    api.get('/analytics/utilization', { params }),
  getPopularResources: (params?: { days?: number; limit?: number }) =>
    api.get('/analytics/popular-resources', { params }),
  getPeakTimes: (params?: { days?: number }) =>
    api.get('/analytics/peak-times', { params }),
  getUserPatterns: (params?: { days?: number }) =>
    api.get('/analytics/user-patterns', { params }),
  exportUtilization: (params?: { days?: number }) =>
    api.get('/analytics/export/utilization.csv', { params, responseType: 'blob' }),
  exportReservations: (params?: { days?: number }) =>
    api.get('/analytics/export/reservations.csv', { params, responseType: 'blob' }),
};

// Business Hours API
export const businessHoursApi = {
  getResourceHours: (resourceId: number) =>
    api.get(`/resources/${resourceId}/business-hours`),
  setResourceHours: (resourceId: number, hours: Array<{
    day_of_week: number;
    open_time: string;
    close_time: string;
    is_closed?: boolean;
  }>) => api.put(`/resources/${resourceId}/business-hours`, { hours }),
  getGlobalHours: () => api.get('/business-hours/global'),
  setGlobalHours: (hours: Array<{
    day_of_week: number;
    open_time: string;
    close_time: string;
    is_closed?: boolean;
  }>) => api.put('/business-hours/global', { hours }),
  getAvailableSlots: (resourceId: number, date: string) =>
    api.get(`/resources/${resourceId}/available-slots`, { params: { date } }),
  getNextAvailable: (resourceId: number) =>
    api.get(`/resources/${resourceId}/next-available`),
  getBlackoutDates: (resourceId?: number) =>
    api.get(resourceId ? `/resources/${resourceId}/blackout-dates` : '/blackout-dates'),
  createBlackoutDate: (data: {
    date: string;
    reason?: string;
    resource_id?: number;
  }) => api.post(data.resource_id ? `/resources/${data.resource_id}/blackout-dates` : '/blackout-dates', data),
  deleteBlackoutDate: (blackoutId: number) =>
    api.delete(`/blackout-dates/${blackoutId}`),
};

// Webhooks API
export const webhooksApi = {
  getEventTypes: () => api.get('/webhooks/events'),
  getSignatureExample: () => api.get('/webhooks/signature-example'),
  list: () => api.get('/webhooks/'),
  get: (webhookId: number) => api.get(`/webhooks/${webhookId}`),
  create: (data: {
    url: string;
    events: string[];
    description?: string;
    is_active?: boolean;
  }) => api.post('/webhooks/', data),
  update: (webhookId: number, data: {
    url?: string;
    events?: string[];
    description?: string;
    is_active?: boolean;
  }) => api.patch(`/webhooks/${webhookId}`, data),
  delete: (webhookId: number) => api.delete(`/webhooks/${webhookId}`),
  regenerateSecret: (webhookId: number) =>
    api.post(`/webhooks/${webhookId}/regenerate-secret`),
  getDeliveries: (webhookId: number) =>
    api.get(`/webhooks/${webhookId}/deliveries`),
  getDeliveryDetails: (webhookId: number, deliveryId: number) =>
    api.get(`/webhooks/${webhookId}/deliveries/${deliveryId}`),
  test: (webhookId: number) => api.post(`/webhooks/${webhookId}/test`),
  retryDelivery: (webhookId: number, deliveryId: number) =>
    api.post(`/webhooks/${webhookId}/deliveries/${deliveryId}/retry`),
};

// Resource Groups API
export const resourceGroupsApi = {
  list: () => api.get('/resource-groups/'),
  getTree: () => api.get('/resource-groups/tree'),
  getBuildings: () => api.get('/resource-groups/buildings'),
  getUngrouped: () => api.get('/resource-groups/ungrouped'),
  get: (groupId: number) => api.get(`/resource-groups/${groupId}`),
  create: (data: {
    name: string;
    description?: string;
    parent_id?: number;
    building?: string;
    floor?: string;
    room?: string;
  }) => api.post('/resource-groups/', data),
  update: (groupId: number, data: {
    name?: string;
    description?: string;
    parent_id?: number;
    building?: string;
    floor?: string;
    room?: string;
  }) => api.patch(`/resource-groups/${groupId}`, data),
  delete: (groupId: number) => api.delete(`/resource-groups/${groupId}`),
  getResources: (groupId: number) =>
    api.get(`/resource-groups/${groupId}/resources`),
  assignResource: (groupId: number, resourceId: number) =>
    api.post(`/resource-groups/${groupId}/resources`, { resource_id: resourceId }),
  removeResource: (groupId: number, resourceId: number) =>
    api.delete(`/resource-groups/${groupId}/resources/${resourceId}`),
  setResourceParent: (resourceId: number, parentId: number | null) =>
    api.post('/resource-groups/resources/set-parent', {
      resource_id: resourceId,
      parent_id: parentId,
    }),
  getResourceChildren: (resourceId: number) =>
    api.get(`/resource-groups/resources/${resourceId}/children`),
};

// Quotas API
export const quotasApi = {
  getConfig: () => api.get('/quotas/config'),
  getMyUsage: () => api.get('/quotas/my-usage'),
  getSummary: () => api.get('/quotas/summary'),
  // Admin endpoints
  listUsers: () => api.get('/quotas/users'),
  getUser: (userId: number) => api.get(`/quotas/users/${userId}`),
  updateUser: (userId: number, data: {
    daily_limit?: number;
    tier?: string;
  }) => api.patch(`/quotas/users/${userId}`, data),
  getStats: () => api.get('/quotas/stats'),
  getAlerts: () => api.get('/quotas/alerts'),
  resetDaily: () => api.post('/quotas/reset-daily'),
};

// User Preferences API
export const userPreferencesApi = {
  get: () => api.get('/users/me'),
  update: (data: {
    email_notifications?: boolean;
    reminder_hours?: number;
  }) => api.patch('/users/me/preferences', data),
};
