'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, Activity, Server, Calendar } from 'lucide-react';

import api from '@/lib/api';

import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';

interface HealthDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    stats: {
        totalResources: number;
        availableResources: number;
        activeReservations: number;
        upcomingReservations: number;
    };
}

interface HealthData {
    status: string;
    timestamp: string;
    details?: Record<string, unknown>;
}

export function HealthDialog({ open, onOpenChange, stats }: HealthDialogProps) {
    const [loading, setLoading] = useState(false);
    const [health, setHealth] = useState<HealthData | null>(null);

    const fetchHealth = async () => {
        setLoading(true);
        try {
            const response = await api.get('/health');
            setHealth({
                ...response.data,
                timestamp: new Date().toISOString(),
            });
        } catch (err) {
            console.error('Failed to fetch health:', err);
            setHealth(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (open) {
            fetchHealth();
        }
    }, [open]);

    const availablePercent = stats.totalResources > 0
        ? Math.round((stats.availableResources / stats.totalResources) * 100)
        : 0;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Activity className="h-5 w-5" />
                        System Health Status
                    </DialogTitle>
                    <DialogDescription>
                        View system status and resource statistics.
                    </DialogDescription>
                </DialogHeader>

                {loading ? (
                    <div className="space-y-4">
                        <Skeleton className="h-16 w-full" />
                        <Skeleton className="h-32 w-full" />
                        <Skeleton className="h-32 w-full" />
                    </div>
                ) : (
                    <div className="space-y-6">
                        {/* System Status */}
                        <Alert className={health?.status === 'healthy' ? 'border-green-500' : 'border-red-500'}>
                            <Server className="h-4 w-4" />
                            <AlertDescription>
                                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                                    <span>
                                        <strong>System Status:</strong>{' '}
                                        <span className={health?.status === 'healthy' ? 'text-green-600' : 'text-red-600'}>
                                            {health?.status === 'healthy' ? 'Running Normally' : 'Issues Detected'}
                                        </span>
                                    </span>
                                </div>
                                {health?.timestamp && (
                                    <div className="text-xs text-muted-foreground mt-1">
                                        Last updated: {new Date(health.timestamp).toLocaleString()}
                                    </div>
                                )}
                            </AlertDescription>
                        </Alert>

                        {/* Resource Statistics */}
                        <div className="space-y-3">
                            <h4 className="font-semibold flex items-center gap-2">
                                <Server className="h-4 w-4 text-primary" />
                                Resource Statistics
                            </h4>
                            <div className="grid grid-cols-1 gap-3 text-center sm:grid-cols-3 sm:gap-4">
                                <div className="rounded-lg border p-3">
                                    <div className="text-2xl font-bold">{stats.totalResources}</div>
                                    <div className="text-xs text-muted-foreground">Total</div>
                                </div>
                                <div className="rounded-lg border p-3">
                                    <div className="text-2xl font-bold text-green-600">{stats.availableResources}</div>
                                    <div className="text-xs text-muted-foreground">Available</div>
                                </div>
                                <div className="rounded-lg border p-3">
                                    <div className="text-2xl font-bold text-orange-600">
                                        {stats.totalResources - stats.availableResources}
                                    </div>
                                    <div className="text-xs text-muted-foreground">Booked</div>
                                </div>
                            </div>
                            <div className="space-y-1">
                                <div className="flex justify-between text-sm">
                                    <span>Availability</span>
                                    <span>{availablePercent}%</span>
                                </div>
                                <Progress value={availablePercent} className="h-2" />
                            </div>
                        </div>

                        {/* Reservation Statistics */}
                        <div className="space-y-3">
                            <h4 className="font-semibold flex items-center gap-2">
                                <Calendar className="h-4 w-4 text-primary" />
                                Reservation Statistics
                            </h4>
                            <div className="grid grid-cols-1 gap-3 text-center sm:grid-cols-2 sm:gap-4">
                                <div className="rounded-lg border p-3">
                                    <div className="text-2xl font-bold text-blue-600">{stats.activeReservations}</div>
                                    <div className="text-xs text-muted-foreground">Active Bookings</div>
                                </div>
                                <div className="rounded-lg border p-3">
                                    <div className="text-2xl font-bold text-purple-600">{stats.upcomingReservations}</div>
                                    <div className="text-xs text-muted-foreground">Upcoming</div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Close
                    </Button>
                    <Button onClick={fetchHealth} disabled={loading}>
                        <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
