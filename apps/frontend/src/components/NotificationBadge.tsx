/**
 * Notification Badge component.
 */

"use client";

import { Bell } from 'lucide-react';

import { useNotifications } from '@/hooks/useNotifications';
import { NotificationCenter } from '@/components/NotificationCenter';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface NotificationBadgeProps {
  enabled?: boolean;
}

export function NotificationBadge({ enabled = true }: NotificationBadgeProps) {
  const {
    notifications,
    unreadCount,
    loading,
    error,
    hasMore,
    loadMore,
    markAsRead,
    markAllAsRead,
  } = useNotifications({ enabled, pageSize: 20 });

  const unreadLabel = unreadCount > 9 ? '9+' : unreadCount;

  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute -right-1 -top-1 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-destructive px-1 text-[11px] font-semibold text-destructive-foreground">
              {unreadLabel}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[380px] p-0">
        <NotificationCenter
          notifications={notifications}
          loading={loading}
          error={error}
          onMarkRead={markAsRead}
          onMarkAllRead={markAllAsRead}
          onLoadMore={loadMore}
          hasMore={hasMore}
        />
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
