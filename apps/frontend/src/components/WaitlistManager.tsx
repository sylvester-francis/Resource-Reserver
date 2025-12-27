/**
 * Waitlist Manager component.
 */

"use client";

import { useState, useEffect, useCallback } from 'react';
import { Clock, Loader2, X, Check, AlertCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { WaitlistStatus } from '@/components/WaitlistStatus';
import { waitlistApi } from '@/lib/api';
import { toast } from 'sonner';
import type { WaitlistEntry, PaginatedResponse } from '@/types';

interface WaitlistManagerProps {
  onReservationCreated?: () => void;
}

export function WaitlistManager({ onReservationCreated }: WaitlistManagerProps) {
  const [entries, setEntries] = useState<WaitlistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [cursor, setCursor] = useState<string | null>(null);

  const fetchEntries = useCallback(async (loadMore = false) => {
    try {
      if (!loadMore) {
        setLoading(true);
      }
      const params: Record<string, unknown> = {
        limit: 10,
        include_completed: false,
        sort_by: 'created_at',
        sort_order: 'desc',
      };
      if (loadMore && cursor) {
        params.cursor = cursor;
      }
      const response = await waitlistApi.list(params);
      const data = response.data as PaginatedResponse<WaitlistEntry>;

      if (loadMore) {
        setEntries(prev => [...prev, ...data.data]);
      } else {
        setEntries(data.data);
      }
      setHasMore(data.has_more);
      setCursor(data.next_cursor || null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load waitlist');
    } finally {
      setLoading(false);
    }
  }, [cursor]);

  useEffect(() => {
    fetchEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLeave = async (id: number) => {
    setActionLoading(id);
    try {
      await waitlistApi.leave(id);
      setEntries(prev => prev.filter(e => e.id !== id));
      toast.success('Left waitlist');
    } catch (err) {
      toast.error('Failed to leave waitlist', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleAccept = async (id: number) => {
    setActionLoading(id);
    try {
      await waitlistApi.accept(id);
      setEntries(prev => prev.filter(e => e.id !== id));
      toast.success('Reservation created!', {
        description: 'Your waitlist offer has been accepted.',
      });
      onReservationCreated?.();
    } catch (err) {
      toast.error('Failed to accept offer', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setActionLoading(null);
    }
  };

  if (loading && entries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Waitlist
          </CardTitle>
          <CardDescription>Loading your waitlist entries...</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error && entries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Waitlist
          </CardTitle>
          <CardDescription className="text-destructive">{error}</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Button onClick={() => fetchEntries()} variant="outline">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (entries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Waitlist
          </CardTitle>
          <CardDescription>
            You&apos;re not on any waitlists. Join a waitlist when a resource is unavailable.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Waitlist
        </CardTitle>
        <CardDescription>
          Manage your waitlist entries and accept offers when resources become available.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className={`flex items-center justify-between rounded-lg border p-4 ${
              entry.status === 'offered' ? 'border-primary bg-primary/5' : ''
            }`}
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">
                  {entry.resource?.name || `Resource #${entry.resource_id}`}
                </span>
                <WaitlistStatus
                  status={entry.status}
                  position={entry.position}
                  expiresAt={entry.offer_expires_at}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                {new Date(entry.desired_start).toLocaleString()} -{' '}
                {new Date(entry.desired_end).toLocaleTimeString()}
              </p>
              {entry.flexible_time && (
                <p className="text-xs text-muted-foreground">
                  Flexible timing enabled
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              {entry.status === 'offered' && (
                <Button
                  size="sm"
                  onClick={() => handleAccept(entry.id)}
                  disabled={actionLoading === entry.id}
                  className="gap-1"
                >
                  {actionLoading === entry.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Check className="h-4 w-4" />
                  )}
                  Accept
                </Button>
              )}
              {(entry.status === 'waiting' || entry.status === 'offered') && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleLeave(entry.id)}
                  disabled={actionLoading === entry.id}
                  className="gap-1"
                >
                  {actionLoading === entry.id && entry.status !== 'offered' ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <X className="h-4 w-4" />
                  )}
                  Leave
                </Button>
              )}
            </div>
          </div>
        ))}
        {hasMore && (
          <div className="flex justify-center pt-2">
            <Button
              variant="outline"
              onClick={() => fetchEntries(true)}
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Load More
            </Button>
          </div>
        )}
        {entries.some(e => e.status === 'offered') && (
          <div className="mt-4 flex items-center gap-2 rounded-md bg-primary/10 p-3 text-sm">
            <AlertCircle className="h-4 w-4 text-primary" />
            <span>
              You have waitlist offers! Accept them before they expire.
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
