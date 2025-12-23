'use client';

import { useCallback, useMemo, useState } from 'react';
import {
    Calendar,
    Clock,
    History,
    X,
    ArrowDownWideNarrow,
    ArrowUpWideNarrow,
} from 'lucide-react';
import { toast } from 'sonner';

import api from '@/lib/api';
import { formatDateTime } from '@/lib/date';
import { usePagination } from '@/hooks/use-pagination';
import type { Reservation } from '@/types';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { HistoryDialog } from '@/components/history-dialog';
import { Pagination } from '@/components/pagination';
import { Skeleton } from '@/components/ui/skeleton';
import { RecurringBadge } from '@/components/RecurringBadge';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';

interface ReservationsTabProps {
    onRefresh: () => void;
    showAll?: boolean;
    upcomingOnly?: boolean;
    emptyMessage?: string;
    emptyDescription?: string;
}

export function ReservationsTab({
    onRefresh,
    showAll = false,
    upcomingOnly = false,
    emptyMessage = 'No Reservations Found',
    emptyDescription = "You haven't made any reservations yet. Start by browsing available resources.",
}: ReservationsTabProps) {
    const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
    const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
    const [selectedReservation, setSelectedReservation] = useState<Reservation | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [sortBy, setSortBy] = useState('start_time');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const timeZoneLabel = Intl.DateTimeFormat().resolvedOptions().timeZone;

    const handleViewHistory = (reservation: Reservation) => {
        setSelectedReservation(reservation);
        setHistoryDialogOpen(true);
    };

    const handleCancelClick = (reservation: Reservation) => {
        setSelectedReservation(reservation);
        setCancelDialogOpen(true);
    };

    const handleCancelConfirm = async () => {
        if (!selectedReservation) return;

        setIsLoading(true);
        try {
            await api.post(`/reservations/${selectedReservation.id}/cancel`, {
                reason: 'Cancelled by user',
            });
            toast.success('Reservation cancelled successfully');
            await refresh();
            onRefresh();
        } catch {
            toast.error('Failed to cancel reservation');
        } finally {
            setIsLoading(false);
            setCancelDialogOpen(false);
        }
    };

    const canCancel = (reservation: Reservation) => {
        return reservation.status === 'active' && new Date(reservation.start_time) > new Date();
    };

    const getStatusVariant = (status: string): 'default' | 'secondary' | 'destructive' | 'outline' => {
        switch (status) {
            case 'active':
                return 'default';
            case 'cancelled':
                return 'destructive';
            case 'expired':
                return 'secondary';
            default:
                return 'outline';
        }
    };

    const pageSize = 10;
    const paginationParams = useMemo(
        () => ({
            include_cancelled: showAll || undefined,
            sort_by: sortBy,
            sort_order: sortOrder,
        }),
        [showAll, sortBy, sortOrder]
    );

    const fetchReservations = useCallback(
        async ({
            cursor,
            limit,
            include_cancelled,
            sort_by,
            sort_order,
        }: {
            cursor?: string | null;
            limit: number;
            include_cancelled?: boolean;
            sort_by?: string;
            sort_order?: string;
        }) => {
            const response = await api.get('/reservations/my', {
                params: {
                    cursor,
                    limit,
                    include_cancelled,
                    sort_by,
                    sort_order,
                },
            });
            return response.data;
        },
        []
    );

    const {
        items: reservations,
        hasMore,
        loading,
        totalCount,
        loadMore,
        refresh,
    } = usePagination<Reservation, typeof paginationParams>(fetchReservations, {
        params: paginationParams,
        limit: pageSize,
    });

    const displayedReservations = useMemo(() => {
        if (!upcomingOnly) return reservations;
        const now = new Date();
        return reservations.filter(
            reservation =>
                reservation.status === 'active' && new Date(reservation.start_time) > now
        );
    }, [reservations, upcomingOnly]);

    return (
        <>
            <Card>
                <CardHeader>
                    <CardTitle>{showAll ? 'My Reservations' : 'Upcoming Reservations'}</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="mb-4 flex gap-2">
                        <Select value={sortBy} onValueChange={setSortBy}>
                            <SelectTrigger className="w-[180px]">
                                <SelectValue placeholder="Sort by" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="start_time">Start time</SelectItem>
                                <SelectItem value="end_time">End time</SelectItem>
                                <SelectItem value="created_at">Created at</SelectItem>
                                <SelectItem value="id">ID</SelectItem>
                            </SelectContent>
                        </Select>
                        <Button
                            variant="secondary"
                            size="sm"
                            className="gap-2 rounded-full border border-primary/30 bg-primary/5 text-sm font-semibold"
                            onClick={() => setSortOrder(order => (order === 'asc' ? 'desc' : 'asc'))}
                        >
                            {sortOrder === 'asc' ? (
                                <>
                                    <ArrowUpWideNarrow className="h-4 w-4" />
                                    Ascending
                                </>
                            ) : (
                                <>
                                    <ArrowDownWideNarrow className="h-4 w-4" />
                                    Descending
                                </>
                            )}
                        </Button>
                    </div>

                    {loading && reservations.length === 0 ? (
                        <div className="space-y-3">
                            {[...Array(3)].map((_, index) => (
                                <Skeleton key={index} className="h-20 w-full" />
                            ))}
                        </div>
                    ) : displayedReservations.length === 0 &&
                      (!upcomingOnly || !hasMore) ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <Calendar className="mb-4 h-12 w-12 text-muted-foreground/50" />
                            <h3 className="text-lg font-semibold">{emptyMessage}</h3>
                            <p className="text-muted-foreground max-w-sm">{emptyDescription}</p>
                        </div>
                    ) : displayedReservations.length === 0 && upcomingOnly ? (
                        <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                            Load more to check additional reservations.
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {displayedReservations.map(reservation => (
                                <div
                                    key={reservation.id}
                                    className="flex items-center justify-between rounded-lg border p-4"
                                >
                                    <div className="space-y-1">
                                        <h3 className="font-medium">
                                            {reservation.resource?.name
                                                ? reservation.resource.name
                                                : `Resource #${reservation.resource_id}`}
                                        </h3>
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                            <Clock className="h-4 w-4" />
                                            <span>{formatDateTime(reservation.start_time)}</span>
                                            <span>-</span>
                                            <span>{formatDateTime(reservation.end_time)}</span>
                                        </div>
                                        <p className="text-xs text-muted-foreground">
                                            All times shown in {timeZoneLabel}
                                        </p>
                                        <Badge variant={getStatusVariant(reservation.status)}>
                                            {reservation.status}
                                        </Badge>
                                        {reservation.recurrence_rule_id ? <RecurringBadge /> : null}
                                    </div>
                                    <div className="flex gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleViewHistory(reservation)}
                                        >
                                            <History className="mr-2 h-4 w-4" />
                                            History
                                        </Button>
                                        {canCancel(reservation) && (
                                            <Button
                                                variant="destructive"
                                                size="sm"
                                                onClick={() => handleCancelClick(reservation)}
                                            >
                                                <X className="mr-2 h-4 w-4" />
                                                Cancel
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    <Pagination
                        hasMore={hasMore}
                        loading={loading}
                        onLoadMore={loadMore}
                        summary={
                            totalCount !== null
                                ? `Showing ${reservations.length} of ${totalCount} reservations`
                                : `Showing ${reservations.length} reservations`
                        }
                    />
                </CardContent>
            </Card>

            {/* History Dialog */}
            <HistoryDialog
                open={historyDialogOpen}
                onOpenChange={setHistoryDialogOpen}
                reservation={selectedReservation}
            />

            {/* Cancel Confirmation */}
            <AlertDialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Cancel Reservation?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to cancel this reservation? This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Keep Reservation</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleCancelConfirm}
                            disabled={isLoading}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {isLoading ? 'Cancelling...' : 'Yes, Cancel'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}
