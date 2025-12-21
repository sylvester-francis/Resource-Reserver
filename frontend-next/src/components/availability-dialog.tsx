'use client';

import { useState, useEffect, useCallback } from 'react';
import { format } from 'date-fns';
import { RefreshCw, Calendar } from 'lucide-react';

import api from '@/lib/api';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
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

            const data = response.data.data || response.data;
            setSchedule(data.reservations || []);
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
            <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle>Resource Availability Schedule</DialogTitle>
                    <DialogDescription>
                        View upcoming reservations for this resource.
                    </DialogDescription>
                </DialogHeader>

                {resource && (
                    <Alert>
                        <AlertDescription>
                            <strong>Resource:</strong> {resource.name}
                            <span className="ml-4">
                                <strong>Status:</strong>{' '}
                                <span className={resource.available ? 'text-green-600' : 'text-red-600'}>
                                    {resource.available ? 'Available' : 'Unavailable'}
                                </span>
                            </span>
                        </AlertDescription>
                    </Alert>
                )}

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Show:</span>
                        <Select value={daysAhead} onValueChange={setDaysAhead}>
                            <SelectTrigger className="w-32">
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
                    </div>
                    <Button variant="outline" size="sm" onClick={fetchAvailability}>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Refresh
                    </Button>
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
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {schedule.map((day, idx) => (
                                <div key={idx} className="rounded-lg border p-4">
                                    <h4 className="mb-3 font-semibold text-sm">
                                        {day.dayName || format(new Date(day.date), 'EEE, MMM d')}
                                    </h4>
                                    <div className="space-y-2">
                                        {day.time_slots.length === 0 ? (
                                            <p className="text-sm text-muted-foreground">No reservations</p>
                                        ) : (
                                            day.time_slots.map((slot, slotIdx) => (
                                                <div
                                                    key={slotIdx}
                                                    className={`flex items-center justify-between rounded px-2 py-1 text-xs ${slot.status === 'available'
                                                            ? 'bg-green-100 dark:bg-green-900/30'
                                                            : 'bg-red-100 dark:bg-red-900/30'
                                                        }`}
                                                >
                                                    <span>
                                                        {slot.start_time} - {slot.end_time}
                                                    </span>
                                                    {slot.user_name && (
                                                        <Badge variant="secondary" className="text-[10px]">
                                                            {slot.user_name}
                                                        </Badge>
                                                    )}
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
