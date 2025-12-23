'use client';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface PaginationProps {
  hasMore: boolean;
  loading: boolean;
  onLoadMore: () => void;
  summary?: string;
  loadMoreLabel?: string;
  className?: string;
}

export function Pagination({
  hasMore,
  loading,
  onLoadMore,
  summary,
  loadMoreLabel = 'Load more',
  className,
}: PaginationProps) {
  if (!summary && !hasMore) {
    return null;
  }

  return (
    <div className={cn('mt-4 flex flex-wrap items-center justify-between gap-2', className)}>
      {summary && <span className="text-sm text-muted-foreground">{summary}</span>}
      {hasMore && (
        <Button variant="outline" size="sm" onClick={onLoadMore} disabled={loading}>
          {loading ? 'Loading...' : loadMoreLabel}
        </Button>
      )}
    </div>
  );
}
