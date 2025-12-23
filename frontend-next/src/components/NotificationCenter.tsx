"use client";

import { Loader2, Inbox } from 'lucide-react';

import { NotificationItem } from '@/components/NotificationItem';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import type { Notification } from '@/types';

interface NotificationCenterProps {
  notifications: Notification[];
  loading?: boolean;
  error?: string | null;
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
}

export function NotificationCenter({
  notifications,
  loading = false,
  error,
  onMarkRead,
  onMarkAllRead,
  onLoadMore,
  hasMore,
}: NotificationCenterProps) {
  const hasNotifications = notifications.length > 0;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between px-3 py-2">
        <div className="space-y-0.5">
          <p className="text-sm font-semibold">Notifications</p>
          <p className="text-xs text-muted-foreground">
            Stay on top of reservations and system updates
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 px-3 text-xs"
          onClick={onMarkAllRead}
          disabled={!hasNotifications}
        >
          Mark all read
        </Button>
      </div>
      <Separator />
      <div className="max-h-[420px] overflow-y-auto p-3">
        {error && (
          <div className="mb-2 rounded-md border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive">
            {error}
          </div>
        )}
        {hasNotifications ? (
          <div className="space-y-3">
            {notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onMarkRead={onMarkRead}
              />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center text-muted-foreground">
            <Inbox className="h-8 w-8" />
            <p className="text-sm">You&apos;re all caught up</p>
            <p className="text-xs text-muted-foreground">
              New alerts about reservations and resources will appear here.
            </p>
          </div>
        )}
        {loading && (
          <div className="mt-3 flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading...
          </div>
        )}
        {hasMore && !loading && (
          <div className="mt-3 flex justify-center">
            <Button variant="outline" size="sm" onClick={onLoadMore}>
              Load more
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
