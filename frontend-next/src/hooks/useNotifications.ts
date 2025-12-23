"use client";

import { useCallback, useEffect, useMemo, useState } from 'react';

import { notificationsApi } from '@/lib/api';
import type { Notification, PaginatedResponse } from '@/types';

type FetchState = 'idle' | 'loading' | 'refreshing';

interface UseNotificationsOptions {
  enabled?: boolean;
  pageSize?: number;
}

export function useNotifications(options: UseNotificationsOptions = {}) {
  const { enabled = true, pageSize = 20 } = options;

  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [state, setState] = useState<FetchState>('idle');
  const [error, setError] = useState<string | null>(null);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.read).length,
    [notifications]
  );

  const fetchPage = useCallback(
    async (cursor: string | null = null, append = false) => {
      if (!enabled) return;
      setError(null);
      setState(cursor && append ? 'refreshing' : 'loading');

      try {
        const response = await notificationsApi.list({
          limit: pageSize,
          cursor: cursor || undefined,
          sort_by: 'created_at',
          sort_order: 'desc',
        });
        const payload = response.data as PaginatedResponse<Notification>;

        setNotifications((prev) =>
          append ? [...prev, ...(payload.data || [])] : payload.data || []
        );
        setNextCursor(payload.next_cursor ?? null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load notifications');
      } finally {
        setState('idle');
      }
    },
    [enabled, pageSize]
  );

  const refresh = useCallback(() => fetchPage(null, false), [fetchPage]);

  const loadMore = useCallback(() => {
    if (!nextCursor || state !== 'idle') return;
    return fetchPage(nextCursor, true);
  }, [fetchPage, nextCursor, state]);

  const markAsRead = useCallback(async (id: number) => {
    try {
      await notificationsApi.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to mark notification');
    }
  }, []);

  const markAllAsRead = useCallback(async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to mark all notifications');
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    (async () => {
      await fetchPage(null, false);
    })();
    return undefined;
  }, [enabled, fetchPage]);

  return {
    notifications,
    unreadCount,
    hasMore: Boolean(nextCursor),
    loading: state !== 'idle',
    error,
    refresh,
    loadMore,
    markAsRead,
    markAllAsRead,
  };
}
