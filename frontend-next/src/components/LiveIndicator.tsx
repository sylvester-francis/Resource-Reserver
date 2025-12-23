'use client';

import { cn } from '@/lib/utils';

type Status = 'connecting' | 'connected' | 'disconnected';

export function LiveIndicator({ status }: { status: Status }) {
  const color =
    status === 'connected'
      ? 'bg-emerald-500 shadow-[0_0_0_6px_rgba(16,185,129,0.25)]'
      : status === 'connecting'
        ? 'bg-amber-400 shadow-[0_0_0_6px_rgba(251,191,36,0.25)]'
        : 'bg-rose-500 shadow-[0_0_0_6px_rgba(244,63,94,0.25)]';

  const label =
    status === 'connected' ? 'Live' : status === 'connecting' ? 'Connecting…' : 'Offline';

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/80 px-3 py-1 text-xs text-muted-foreground',
      )}
      title="WebSocket connection status"
    >
      <span className={cn('h-2.5 w-2.5 rounded-full transition-all duration-300', color)} />
      <span className="font-medium text-foreground">{label}</span>
    </div>
  );
}
