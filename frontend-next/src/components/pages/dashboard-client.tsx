'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Calendar, LogOut, Activity, Settings, CheckCircle2, Clock, Shield } from 'lucide-react';
import { toast } from 'sonner';

import { useAuth } from '@/hooks/use-auth';
import api from '@/lib/api';
import { formatDateTime } from '@/lib/date';
import type { PaginatedResponse, Reservation } from '@/types';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import { ThemeToggle } from '@/components/theme-toggle';
import { ResourcesTab } from '@/components/resources-tab';
import { ReservationsTab } from '@/components/reservations-tab';
import { HealthDialog } from '@/components/health-dialog';
import { MfaDialog } from '@/components/mfa-dialog';

interface Stats {
    totalResources: number;
    availableResources: number;
    activeReservations: number;
    upcomingReservations: number;
}

export default function DashboardClient() {
    const router = useRouter();
    const { user, loading: authLoading, logout, isAuthenticated } = useAuth();

    const [reservations, setReservations] = useState<Reservation[]>([]);
    const [stats, setStats] = useState<Stats>({
        totalResources: 0,
        availableResources: 0,
        activeReservations: 0,
        upcomingReservations: 0,
    });
    const [loading, setLoading] = useState(true);
    const [healthDialogOpen, setHealthDialogOpen] = useState(false);
    const [mfaDialogOpen, setMfaDialogOpen] = useState(false);

    const fetchData = useCallback(async () => {
        const fetchActiveReservations = async () => {
            const allReservations: Reservation[] = [];
            let cursor: string | null = null;
            let hasMore = true;

            while (hasMore) {
                const { data: payload }: { data: PaginatedResponse<Reservation> } = await api.get(
                    '/reservations/my',
                    {
                        params: {
                            limit: 100,
                            cursor,
                            sort_by: 'start_time',
                            sort_order: 'asc',
                        },
                    }
                );
                const data = Array.isArray(payload?.data) ? payload.data : [];
                allReservations.push(...data);
                cursor = payload?.next_cursor ?? null;
                hasMore = Boolean(payload?.has_more);
            }

            return allReservations;
        };

        try {
            const [summaryRes, activeReservations] = await Promise.all([
                api.get('/resources/availability/summary'),
                fetchActiveReservations(),
            ]);

            const summary = summaryRes.data || {};
            const now = new Date();
            const upcomingReservations = activeReservations.filter(
                reservation => new Date(reservation.start_time) > now
            );

            setReservations(activeReservations);
            setStats({
                totalResources: summary.total_resources ?? 0,
                availableResources: summary.available_now ?? 0,
                activeReservations: activeReservations.length,
                upcomingReservations: upcomingReservations.length,
            });
        } catch (err) {
            console.error('Failed to fetch dashboard data:', err);
            toast.error('Failed to load dashboard data');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!authLoading) {
            if (!isAuthenticated) {
                router.replace('/login');
            } else {
                fetchData();
            }
        }
    }, [authLoading, isAuthenticated, router, fetchData]);

    const handleLogout = () => {
        logout();
        toast.success('Signed out successfully');
    };

    if (authLoading || loading) {
        return (
            <div className="min-h-screen">
                <header className="border-b border-border/60 bg-background/80 backdrop-blur">
                    <div className="container mx-auto flex h-16 items-center justify-between px-4">
                        <Skeleton className="h-8 w-48" />
                        <Skeleton className="h-10 w-10 rounded-full" />
                    </div>
                </header>
                <main className="container mx-auto p-4 sm:p-6">
                    <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        {[...Array(4)].map((_, i) => (
                            <Card key={i}>
                                <CardContent className="p-6">
                                    <Skeleton className="mb-2 h-8 w-16" />
                                    <Skeleton className="h-4 w-24" />
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                    <Skeleton className="h-96 w-full" />
                </main>
            </div>
        );
    }

    const upcomingReservations = reservations.filter(
        r => r.status === 'active' && new Date(r.start_time) > new Date()
    );

    return (
        <div className="min-h-screen">
            {/* Header */}
            <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur">
                <div className="container mx-auto flex h-16 items-center justify-between px-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                            <Calendar className="h-5 w-5" />
                        </div>
                        <div className="leading-tight">
                            <p className="font-display text-lg">Resource Reserver</p>
                            <p className="text-xs text-muted-foreground">Smart scheduling hub</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setHealthDialogOpen(true)}
                            title="System Status"
                        >
                            <Activity className="h-4 w-4" />
                        </Button>
                        <ThemeToggle />

                        <DropdownMenu modal={false}>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                                    <Avatar className="h-9 w-9">
                                        <AvatarFallback className="bg-primary text-primary-foreground">
                                            {user?.username?.charAt(0).toUpperCase() || 'U'}
                                        </AvatarFallback>
                                    </Avatar>
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent className="w-56" align="end" side="bottom">
                                <div className="flex items-center gap-2 p-2">
                                    <Avatar className="h-8 w-8">
                                        <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                                            {user?.username?.charAt(0).toUpperCase() || 'U'}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="flex flex-col">
                                        <span className="text-sm font-medium">{user?.username}</span>
                                        <span className="text-xs text-muted-foreground">
                                            {user?.mfa_enabled ? 'MFA enabled' : 'MFA disabled'}
                                        </span>
                                    </div>
                                </div>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={() => setMfaDialogOpen(true)}>
                                    <Settings className="mr-2 h-4 w-4" />
                                    Security Settings
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => router.push('/admin/roles')}>
                                    <Shield className="mr-2 h-4 w-4" />
                                    Role Management
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={handleLogout} className="text-red-600">
                                    <LogOut className="mr-2 h-4 w-4" />
                                    Sign Out
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="container mx-auto p-4 sm:p-6">
                <div className="mb-8 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
                    <Card className="relative overflow-hidden">
                        <CardContent className="space-y-4 p-6">
                            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                Workspace overview
                            </p>
                            <div>
                                <h1 className="font-display text-3xl sm:text-4xl">
                                    Welcome back, {user?.username || 'there'}.
                                </h1>
                                <p className="mt-2 text-muted-foreground">
                                    Track live availability, manage reservations, and stay ahead of conflicts.
                                </p>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/70 px-3 py-1 text-xs text-muted-foreground">
                                    <span className="font-semibold tabular-nums text-foreground">
                                        {stats.availableResources}
                                    </span>
                                    available now
                                </span>
                                <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/70 px-3 py-1 text-xs text-muted-foreground">
                                    <span className="font-semibold tabular-nums text-foreground">
                                        {stats.activeReservations}
                                    </span>
                                    active bookings
                                </span>
                                <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/70 px-3 py-1 text-xs text-muted-foreground">
                                    <span className="font-semibold tabular-nums text-foreground">
                                        {stats.upcomingReservations}
                                    </span>
                                    upcoming
                                </span>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent className="space-y-3 p-6">
                            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                Next reservation
                            </p>
                            {upcomingReservations[0] ? (
                                <div className="space-y-2">
                                    <p className="font-display text-2xl">
                                        Resource #{upcomingReservations[0].resource_id}
                                    </p>
                                    <p className="text-sm text-muted-foreground">
                                        {formatDateTime(upcomingReservations[0].start_time)} —{' '}
                                        {formatDateTime(upcomingReservations[0].end_time)}
                                    </p>
                                </div>
                            ) : (
                                <p className="text-sm text-muted-foreground">
                                    No upcoming reservations yet. Reserve a resource to get started.
                                </p>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Stats Grid */}
                <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {[
                        {
                            label: 'Total Resources',
                            value: stats.totalResources,
                            icon: Calendar,
                        },
                        {
                            label: 'Available Now',
                            value: stats.availableResources,
                            icon: CheckCircle2,
                        },
                        {
                            label: 'Active Bookings',
                            value: stats.activeReservations,
                            icon: Activity,
                        },
                        {
                            label: 'Upcoming',
                            value: stats.upcomingReservations,
                            icon: Clock,
                        },
                    ].map(({ label, value, icon: Icon }) => (
                        <Card key={label}>
                            <CardContent className="flex items-center justify-between p-6">
                                <div>
                                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                                        {label}
                                    </p>
                                    <p className="mt-2 text-3xl font-semibold">{value}</p>
                                </div>
                                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                                    <Icon className="h-5 w-5" />
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* Tabs */}
                <Tabs defaultValue="resources" className="w-full">
                    <TabsList className="mb-4 w-full justify-between lg:w-auto lg:justify-start">
                        <TabsTrigger value="resources" className="gap-2">
                            <Calendar className="h-4 w-4" />
                            Resources
                        </TabsTrigger>
                        <TabsTrigger value="reservations" className="gap-2">
                            My Reservations
                        </TabsTrigger>
                        <TabsTrigger value="upcoming" className="gap-2">
                            Upcoming
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="resources">
                        <ResourcesTab onRefresh={fetchData} />
                    </TabsContent>

                    <TabsContent value="reservations">
                        <ReservationsTab onRefresh={fetchData} showAll />
                    </TabsContent>

                    <TabsContent value="upcoming">
                        <ReservationsTab
                            onRefresh={fetchData}
                            upcomingOnly
                            emptyMessage="No upcoming reservations"
                            emptyDescription="You don't have any upcoming reservations. Book a resource now to secure your spot."
                        />
                    </TabsContent>
                </Tabs>
            </main>

            {/* Dialogs */}
            <HealthDialog
                open={healthDialogOpen}
                onOpenChange={setHealthDialogOpen}
                stats={stats}
            />
            <MfaDialog
                open={mfaDialogOpen}
                onOpenChange={setMfaDialogOpen}
                user={user}
            />
        </div>
    );
}
