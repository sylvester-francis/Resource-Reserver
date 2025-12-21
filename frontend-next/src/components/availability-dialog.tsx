'use client';

import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Calendar } from 'lucide-react';

import api from '@/lib/api';
import { formatDateKey, formatShortDay, formatTime } from '@/lib/date';
import type { Resource } from '@/types';

import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';

interface AvailabilityDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    resource: Resource | null;
}

interface TimeSlot {
    id?: number;
    start_time: string;
    end_time: string;
    status: 'available' | 'booked';
    user_name?: string;
}

interface DaySchedule {
    date: string;
    dayName: string;
    time_slots: TimeSlot[];
}

export function AvailabilityDialog({
    open,
    onOpenChange,
    resource,
}: AvailabilityDialogProps) {
    const [daysAhead, setDaysAhead] = useState('7');
    const [loading, setLoading] = useState(false);
    const [schedule, setSchedule] = useState<DaySchedule[]>([]);

    const fetchAvailability = useCallback(async () => {
        if (!resource) return;

        setLoading(true);
        try {
            const response = await api.get(`/resources/${resource.id}/availability`, {
                params: { days_ahead: parseInt(daysAhead) },
            });

            const payload = response.data?.data ?? response.data ?? {};
            const reservations = Array.isArray(payload.reservations) ? payload.reservations : [];
            const grouped = new Map<string, DaySchedule>();

            reservations.forEach((reservation: TimeSlot & { start_time: string; end_time: string }) => {
                const dateKey = formatDateKey(reservation.start_time);
                const dayName = formatShortDay(reservation.start_time);
                const slot: TimeSlot = {
                    id: reservation.id,
                    start_time: formatTime(reservation.start_time, reservation.start_time),
                    end_time: formatTime(reservation.end_time, reservation.end_time),
                    status: 'booked',
                    user_name: reservation.user_name,
                };

                if (!grouped.has(dateKey)) {
                    grouped.set(dateKey, {
                        date: dateKey,
                        dayName,
                        time_slots: [slot],
                    });
                } else {
                    grouped.get(dateKey)?.time_slots.push(slot);
                }
            });

            setSchedule(Array.from(grouped.values()));
        } catch (err) {
            console.error('Failed to fetch availability:', err);
            setSchedule([]);
        } finally {
            setLoading(false);
        }
    }, [resource, daysAhead]);

    useEffect(() => {
        if (open && resource) {
            fetchAvailability();
        }
    }, [open, resource, fetchAvailability]);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-4xl max-h-[calc(100dvh-2rem)] sm:max-h-[calc(100dvh-4rem)] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle>Resource Availability Schedule</DialogTitle>
                    <DialogDescription>
                        View upcoming reservations for this resource.
                    </DialogDescription>
                </DialogHeader>

                <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border bg-card px-4 py-3">
                    {resource && (
                        <div className="flex flex-wrap items-center gap-3">
                            <div>
                                <p className="text-xs uppercase tracking-wide text-muted-foreground">Resource</p>
                                <p className="font-medium">{resource.name}</p>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">Status</span>
                                <Badge variant={resource.available ? 'default' : 'destructive'}>
                                    {resource.available ? 'Available' : 'Unavailable'}
                                </Badge>
                            </div>
                        </div>
                    )}
                    <div className="flex items-center gap-2">
                        <span className="text-xs uppercase tracking-wide text-muted-foreground">Show</span>
                        <Select value={daysAhead} onValueChange={setDaysAhead}>
                            <SelectTrigger className="w-28">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="3">3 Days</SelectItem>
                                <SelectItem value="7">1 Week</SelectItem>
                                <SelectItem value="14">2 Weeks</SelectItem>
                                <SelectItem value="30">1 Month</SelectItem>
                                <SelectItem value="60">2 Months</SelectItem>
                            </SelectContent>
                        </Select>
                        <Button variant="outline" size="sm" onClick={fetchAvailability}>
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Refresh
                        </Button>
                    </div>
                </div>

                <div className="flex-1 overflow-auto">
                    {loading ? (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {[...Array(6)].map((_, i) => (
                                <Skeleton key={i} className="h-40 w-full" />
                            ))}
                        </div>
                    ) : schedule.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <Calendar className="mb-4 h-12 w-12 text-muted-foreground/50" />
                            <h3 className="text-lg font-semibold">No Schedule Data</h3>
                            <p className="text-muted-foreground">
                                No reservations found for this time period.
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {schedule.map((day, idx) => {
                                const timeSlots = Array.isArray(day.time_slots) ? day.time_slots : [];
                                return (
                                    <div key={idx} className="space-y-2">
                                        <h4 className="text-sm font-semibold">
                                            {day.dayName || formatShortDay(day.date)}
                                        </h4>
                                        <div className="divide-y rounded-lg border bg-card">
                                            {timeSlots.length === 0 ? (
                                                <p className="px-4 py-3 text-sm text-muted-foreground">No reservations</p>
                                            ) : (
                                                timeSlots.map((slot, slotIdx) => (
                                                    <div
                                                        key={slotIdx}
                                                        className={`flex flex-col gap-1 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between ${slot.status === 'available'
                                                                ? 'text-green-700 dark:text-green-300'
                                                                : 'text-foreground'
                                                            }`}
                                                    >
                                                        <span className="font-medium">
                                                            {slot.start_time} - {slot.end_time}
                                                        </span>
                                                        {slot.user_name ? (
                                                            <span className="text-xs text-muted-foreground">
                                                                {slot.user_name}
                                                            </span>
                                                        ) : null}
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
