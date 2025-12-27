/**
 * Waitlist Status component.
 */

"use client";

import { Badge } from '@/components/ui/badge';
import type { WaitlistStatus as WaitlistStatusType } from '@/types';

interface WaitlistStatusProps {
  status: WaitlistStatusType;
  position?: number;
  expiresAt?: string | null;
}

export function WaitlistStatus({ status, position, expiresAt }: WaitlistStatusProps) {
  const getStatusVariant = (): 'default' | 'secondary' | 'destructive' | 'outline' => {
    switch (status) {
      case 'waiting':
        return 'secondary';
      case 'offered':
        return 'default';
      case 'fulfilled':
        return 'default';
      case 'expired':
      case 'cancelled':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getStatusLabel = (): string => {
    switch (status) {
      case 'waiting':
        return position ? `#${position} in queue` : 'Waiting';
      case 'offered':
        return 'Offer available!';
      case 'fulfilled':
        return 'Fulfilled';
      case 'expired':
        return 'Expired';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status;
    }
  };

  const getRemainingTime = (): string | null => {
    if (status !== 'offered' || !expiresAt) return null;
    const expiry = new Date(expiresAt);
    const now = new Date();
    const diffMs = expiry.getTime() - now.getTime();
    if (diffMs <= 0) return 'Expired';
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Less than a minute';
    return `${diffMins} min remaining`;
  };

  const remainingTime = getRemainingTime();

  return (
    <div className="flex items-center gap-2">
      <Badge variant={getStatusVariant()}>
        {getStatusLabel()}
      </Badge>
      {remainingTime && status === 'offered' && (
        <span className="text-xs text-muted-foreground animate-pulse">
          {remainingTime}
        </span>
      )}
    </div>
  );
}
