'use client';

import { useState } from 'react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import { reservationsApi } from '@/lib/api';
import type { RecurrenceRule, Resource } from '@/types';
import { RecurrenceSelector } from '@/components/RecurrenceSelector';

import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface ReservationDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    resource: Resource | null;
    onSuccess: () => void;
}

export function ReservationDialog({
    open,
    onOpenChange,
    resource,
    onSuccess,
}: ReservationDialogProps) {
    // Default to today and next hour
    const now = new Date();
    const nextHour = new Date(now.getTime() + 60 * 60 * 1000);

    const [startDate, setStartDate] = useState(format(now, 'yyyy-MM-dd'));
    const [startTime, setStartTime] = useState(format(nextHour, 'HH:00'));
    const [endDate, setEndDate] = useState(format(now, 'yyyy-MM-dd'));
    const [endTime, setEndTime] = useState(format(new Date(nextHour.getTime() + 60 * 60 * 1000), 'HH:00'));
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [recurring, setRecurring] = useState(false);
    const [recurrenceRule, setRecurrenceRule] = useState<RecurrenceRule>({
        frequency: 'daily',
        interval: 1,
        end_type: 'after_count',
        occurrence_count: 5,
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!resource) return;

        setError(null);

        // Combine date and time
        const startDateTime = new Date(`${startDate}T${startTime}`);
        const endDateTime = new Date(`${endDate}T${endTime}`);

        // Validation
        if (startDateTime >= endDateTime) {
            setError('End time must be after start time');
            return;
        }

        if (startDateTime < new Date()) {
            setError('Start time cannot be in the past');
            return;
        }

        setIsLoading(true);

        try {
            const payload = {
                resource_id: resource.id,
                start_time: startDateTime.toISOString(),
                end_time: endDateTime.toISOString(),
            };

            if (recurring) {
                await reservationsApi.createRecurring({
                    ...payload,
                    recurrence: recurrenceRule,
                });
            } else {
                await reservationsApi.create(payload);
            }

            toast.success('Reservation created successfully');
            onSuccess();
            onOpenChange(false);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to create reservation';
            setError(message);
            toast.error(message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Create Reservation</DialogTitle>
                    <DialogDescription>
                        Book this resource for your desired time slot.
                    </DialogDescription>
                </DialogHeader>

                {resource && (
                    <Alert>
                        <AlertDescription>
                            <strong>Selected Resource:</strong> {resource.name}
                        </AlertDescription>
                    </Alert>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <div className="grid gap-2">
                                <Label htmlFor="start-date">Start Date</Label>
                                <Input
                                    id="start-date"
                                    type="date"
                                    value={startDate}
                                    onChange={e => setStartDate(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="start-time">Start Time</Label>
                                <Input
                                    id="start-time"
                                    type="time"
                                    value={startTime}
                                    onChange={e => setStartTime(e.target.value)}
                                    required
                                />
                            </div>
                        </div>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <div className="grid gap-2">
                                <Label htmlFor="end-date">End Date</Label>
                                <Input
                                    id="end-date"
                                    type="date"
                                    value={endDate}
                                    onChange={e => setEndDate(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="end-time">End Time</Label>
                                <Input
                                    id="end-time"
                                    type="time"
                                    value={endTime}
                                    onChange={e => setEndTime(e.target.value)}
                                    required
                                />
                            </div>
                        </div>
                        <RecurrenceSelector
                            enabled={recurring}
                            value={recurrenceRule}
                            onToggle={setRecurring}
                            onChange={setRecurrenceRule}
                        />
                        {error && (
                            <p className="text-sm text-destructive">{error}</p>
                        )}
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isLoading}>
                            {isLoading ? 'Creating...' : 'Create Reservation'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
