/**
 * Recurring Badge component.
 */

"use client";

import { Repeat } from 'lucide-react';

import { Badge } from '@/components/ui/badge';

export function RecurringBadge() {
  return (
    <Badge variant="outline" className="gap-1 text-xs">
      <Repeat className="h-3 w-3" />
      Recurring
    </Badge>
  );
}
