'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { User } from '@/types';

// Token storage helpers
const TOKEN_COOKIE_MAX_AGE = 30 * 60; // 30 minutes for access token
const REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60; // 7 days for refresh token

function setAuthCookies(accessToken: string, refreshToken: string) {
  if (typeof window === 'undefined') return;
  document.cookie = `auth_token=${accessToken}; path=/; max-age=${TOKEN_COOKIE_MAX_AGE}; SameSite=Lax`;
  document.cookie = `refresh_token=${refreshToken}; path=/; max-age=${REFRESH_TOKEN_MAX_AGE}; SameSite=Lax`;
}

function clearAuthCookies() {
  if (typeof window === 'undefined') return;
  document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
  document.cookie = 'refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  const match = document.cookie.match(/refresh_token=([^;]+)/);
  return match ? match[1] : null;
}

export const redirectToLogin = () => {
  if (typeof window === 'undefined') return;
  const isJsDom = typeof navigator !== 'undefined' && navigator.userAgent?.includes('jsdom');

  if (isJsDom) {
    try {
      window.history.pushState({}, '', '/login');
    } catch {
      // Ignore navigation errors in non-browser environments.
    }
    return;
  }

  try {
    window.location.assign('/login');
  } catch {
    try {
      window.history.pushState({}, '', '/login');
    } catch {
      // Ignore navigation errors in non-browser environments.
    }
  }
};

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    if (typeof window === 'undefined') {
      // Skip auth check on server
      setLoading(false);
      return;
    }

    try {
      const response = await api.get('/users/me');
      setUser(response.data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (username: string, password: string, mfaCode?: string) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    if (mfaCode) {
      formData.append('mfa_code', mfaCode);
    }

    const response = await api.post('/token', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    // Store both tokens in cookies
    if (typeof window !== 'undefined' && response.data.access_token && response.data.refresh_token) {
      setAuthCookies(response.data.access_token, response.data.refresh_token);
    }

    await checkAuth();
    return response.data;
  };

  const register = async (username: string, password: string) => {
    const response = await api.post('/register', { username, password });
    return response.data;
  };

  const logout = async () => {
    // Call logout endpoint to revoke refresh tokens
    try {
      await api.post('/logout');
    } catch {
      // Continue with local logout even if API call fails
    }

    // Clear auth cookies
    clearAuthCookies();
    setUser(null);

    redirectToLogin();
  };

  return {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    checkAuth,
  };
}
