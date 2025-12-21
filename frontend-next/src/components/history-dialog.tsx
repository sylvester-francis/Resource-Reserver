'use client';

import { useState, useEffect, useCallback } from 'react';
import { History, CheckCircle, XCircle, Clock, Edit } from 'lucide-react';

import api from '@/lib/api';
import { formatDateTime } from '@/lib/date';
import type { Reservation } from '@/types';

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';

interface HistoryDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    reservation: Reservation | null;
}

interface HistoryEntry {
    id: number;
    action: string;
    timestamp: string;
    details?: string;
}

export function HistoryDialog({
    open,
    onOpenChange,
    reservation,
}: HistoryDialogProps) {
    const [loading, setLoading] = useState(false);
    const [history, setHistory] = useState<HistoryEntry[]>([]);

    const fetchHistory = useCallback(async () => {
        if (!reservation) return;

        setLoading(true);
        try {
            const response = await api.get(`/reservations/${reservation.id}/history`);
            setHistory(response.data || []);
        } catch (err) {
            console.error('Failed to fetch history:', err);
            setHistory([]);
        } finally {
            setLoading(false);
        }
    }, [reservation]);

    useEffect(() => {
        if (open && reservation) {
            fetchHistory();
        }
    }, [open, reservation, fetchHistory]);

    const getActionIcon = (action: string) => {
        switch (action.toLowerCase()) {
            case 'created':
                return <CheckCircle className="h-4 w-4 text-green-500" />;
            case 'cancelled':
                return <XCircle className="h-4 w-4 text-red-500" />;
            case 'modified':
            case 'updated':
                return <Edit className="h-4 w-4 text-blue-500" />;
            default:
                return <Clock className="h-4 w-4 text-gray-500" />;
        }
    };

    const getActionText = (action: string) => {
        switch (action.toLowerCase()) {
            case 'created':
                return 'Reservation Created';
            case 'cancelled':
                return 'Reservation Cancelled';
            case 'modified':
            case 'updated':
                return 'Reservation Modified';
            case 'expired':
                return 'Reservation Expired';
            default:
                return action.charAt(0).toUpperCase() + action.slice(1);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Reservation History</DialogTitle>
                    <DialogDescription>
                        View the activity timeline for this reservation.
                    </DialogDescription>
                </DialogHeader>

                {reservation && (
                    <Alert>
                        <AlertDescription>
                            <div className="space-y-1">
                                <div>
                                    <strong>Resource:</strong> #{reservation.resource_id}
                                </div>
                                <div>
                                    <strong>Period:</strong> {formatDateTime(reservation.start_time)} -{' '}
                                    {formatDateTime(reservation.end_time)}
                                </div>
                                <div>
                                    <strong>Status:</strong>{' '}
                                    <Badge
                                        variant={
                                            reservation.status === 'active'
                                                ? 'default'
                                                : reservation.status === 'cancelled'
                                                    ? 'destructive'
                                                    : 'secondary'
                                        }
                                    >
                                        {reservation.status}
                                    </Badge>
                                </div>
                            </div>
                        </AlertDescription>
                    </Alert>
                )}

                <div className="max-h-[300px] overflow-auto">
                    {loading ? (
                        <div className="space-y-4">
                            {[...Array(3)].map((_, i) => (
                                <div key={i} className="flex gap-3">
                                    <Skeleton className="h-8 w-8 rounded-full" />
                                    <div className="flex-1 space-y-2">
                                        <Skeleton className="h-4 w-3/4" />
                                        <Skeleton className="h-3 w-1/2" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : history.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-8 text-center">
                            <History className="mb-4 h-12 w-12 text-muted-foreground/50" />
                            <h3 className="text-lg font-semibold">No History Available</h3>
                            <p className="text-muted-foreground">
                                This reservation has no recorded history yet.
                            </p>
                        </div>
                    ) : (
                        <div className="relative">
                            {/* Timeline line */}
                            <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />

                            <div className="space-y-4">
                                {history.map((entry, idx) => (
                                    <div key={entry.id || idx} className="relative flex gap-4 pl-10">
                                        {/* Timeline dot */}
                                        <div className="absolute left-0 flex h-8 w-8 items-center justify-center rounded-full bg-background border">
                                            {getActionIcon(entry.action)}
                                        </div>

                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <span className="font-medium">{getActionText(entry.action)}</span>
                                            </div>
                                            <div className="text-sm text-muted-foreground">
                                                {formatDateTime(entry.timestamp)}
                                            </div>
                                            {entry.details && (
                                                <p className="mt-1 text-sm text-muted-foreground">{entry.details}</p>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
