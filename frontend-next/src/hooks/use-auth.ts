'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { User } from '@/types';

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

    // Store token in cookie
    if (typeof window !== 'undefined') {
      document.cookie = `auth_token=${response.data.access_token}; path=/; max-age=${24 * 60 * 60}; SameSite=Lax`;
    }

    await checkAuth();
    return response.data;
  };

  const register = async (username: string, password: string) => {
    const response = await api.post('/register', { username, password });
    return response.data;
  };

  const logout = () => {
    // Clear auth cookie
    if (typeof window !== 'undefined') {
      document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
      setUser(null);
      window.location.href = '/login';
    }
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
