'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { PaginatedResponse } from '@/types';

type FetchPage<T, Params> = (
  params: Params & { cursor?: string | null; limit: number }
) => Promise<PaginatedResponse<T>>;

interface UsePaginationOptions<Params> {
  params?: Params;
  limit?: number;
  enabled?: boolean;
}

export function usePagination<T, Params extends Record<string, unknown>>(
  fetchPage: FetchPage<T, Params>,
  { params, limit = 20, enabled = true }: UsePaginationOptions<Params> = {}
) {
  const [items, setItems] = useState<T[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [totalCount, setTotalCount] = useState<number | null>(null);

  const paramsKey = useMemo(() => JSON.stringify(params ?? {}), [params]);
  const paramsRef = useRef(params ?? ({} as Params));
  const loadingRef = useRef(false);

  useEffect(() => {
    paramsRef.current = params ?? ({} as Params);
  }, [paramsKey, params]);

  const loadPage = useCallback(
    async (nextCursor: string | null, replace: boolean) => {
      if (!enabled || loadingRef.current) return;
      loadingRef.current = true;
      setLoading(true);
      setError(null);

      try {
        const response = await fetchPage({
          ...(paramsRef.current as Params),
          cursor: nextCursor ?? undefined,
          limit,
        });

        setItems((prev) => (replace ? response.data : [...prev, ...response.data]));
        setCursor(response.next_cursor ?? null);
        setHasMore(response.has_more);

        if (typeof response.total_count === 'number') {
          setTotalCount(response.total_count);
        } else if (replace) {
          setTotalCount(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to load data'));
      } finally {
        loadingRef.current = false;
        setLoading(false);
      }
    },
    [fetchPage, limit, enabled]
  );

  const loadMore = useCallback(() => {
    if (!hasMore || loadingRef.current) return;
    void loadPage(cursor, false);
  }, [cursor, hasMore, loadPage]);

  const refresh = useCallback(async () => {
    setItems([]);
    setCursor(null);
    setHasMore(true);
    setTotalCount(null);
    await loadPage(null, true);
  }, [loadPage]);

  useEffect(() => {
    if (!enabled) return;
    void refresh();
  }, [paramsKey, limit, enabled, refresh]);

  return {
    items,
    hasMore,
    loading,
    error,
    totalCount,
    loadMore,
    refresh,
  };
}
