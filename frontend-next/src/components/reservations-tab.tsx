'use client';

import { useState } from 'react';
import { Calendar, Clock, History, X } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import api from '@/lib/api';
import type { Reservation } from '@/types';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { HistoryDialog } from '@/components/history-dialog';
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

interface ReservationsTabProps {
    reservations: Reservation[];
    onRefresh: () => void;
    showAll?: boolean;
    emptyMessage?: string;
    emptyDescription?: string;
}

export function ReservationsTab({
    reservations,
    onRefresh,
    showAll = false,
    emptyMessage = 'No Reservations Found',
    emptyDescription = "You haven't made any reservations yet. Start by browsing available resources.",
}: ReservationsTabProps) {
    const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
    const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
    const [selectedReservation, setSelectedReservation] = useState<Reservation | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    const formatDateTime = (dateString: string) => {
        return format(new Date(dateString), 'MMM d, yyyy h:mm a');
    };

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
            onRefresh();
        } catch (err) {
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

    return (
        <>
            <Card>
                <CardHeader>
                    <CardTitle>{showAll ? 'My Reservations' : 'Upcoming Reservations'}</CardTitle>
                </CardHeader>
                <CardContent>
                    {reservations.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <Calendar className="mb-4 h-12 w-12 text-muted-foreground/50" />
                            <h3 className="text-lg font-semibold">{emptyMessage}</h3>
                            <p className="text-muted-foreground max-w-sm">{emptyDescription}</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {reservations.map(reservation => (
                                <div
                                    key={reservation.id}
                                    className="flex items-center justify-between rounded-lg border p-4"
                                >
                                    <div className="space-y-1">
                                        <h3 className="font-medium">Resource #{reservation.resource_id}</h3>
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                            <Clock className="h-4 w-4" />
                                            <span>{formatDateTime(reservation.start_time)}</span>
                                            <span>-</span>
                                            <span>{formatDateTime(reservation.end_time)}</span>
                                        </div>
                                        <Badge variant={getStatusVariant(reservation.status)}>
                                            {reservation.status}
                                        </Badge>
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
