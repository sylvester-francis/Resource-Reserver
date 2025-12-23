"use client";

import { Bell, CheckCircle2 } from 'lucide-react';

import { formatDateTime } from '@/lib/date';
import type { Notification } from '@/types';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface NotificationItemProps {
  notification: Notification;
  onMarkRead?: (id: number) => void;
}

export function NotificationItem({ notification, onMarkRead }: NotificationItemProps) {
  const { id, title, message, created_at, read, type } = notification;

  return (
    <div
      className={`rounded-lg border border-border/60 bg-card/70 p-3 transition hover:border-border ${
        !read ? 'shadow-[0_10px_30px_-20px_rgba(0,0,0,0.5)]' : ''
      }`}
    >
      <div className="mb-1 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-primary/10 p-1.5 text-primary">
            <Bell className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-semibold leading-tight">{title}</p>
            <p className="text-xs text-muted-foreground">{formatDateTime(created_at)}</p>
          </div>
        </div>
        <Badge variant="outline" className="text-[11px] capitalize">
          {type.replace('_', ' ')}
        </Badge>
      </div>
      <p className="text-sm text-muted-foreground">{message}</p>
      <div className="mt-3 flex items-center justify-between">
        {!read ? (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 text-xs"
            onClick={() => onMarkRead?.(id)}
          >
            <CheckCircle2 className="mr-2 h-4 w-4" />
            Mark as read
          </Button>
        ) : (
          <span className="flex items-center gap-2 text-xs text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            Read
          </span>
        )}
      </div>
    </div>
  );
}
