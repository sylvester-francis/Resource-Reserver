'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Calendar, LogOut, Activity, Settings } from 'lucide-react';
import { toast } from 'sonner';

import { useAuth } from '@/hooks/use-auth';
import api from '@/lib/api';
import type { Resource, Reservation } from '@/types';

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

    const [resources, setResources] = useState<Resource[]>([]);
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
        try {
            const [allResourcesRes, availableResourcesRes, reservationsRes] = await Promise.all([
                api.get('/resources/search', { params: { status: 'all' } }),
                api.get('/resources/search', { params: { status: 'available' } }),
                api.get('/reservations/my'),
            ]);

            const allResources = allResourcesRes.data as Resource[];
            const availableResources = availableResourcesRes.data as Resource[];
            const myReservations = reservationsRes.data as Reservation[];

            setResources(allResources);
            setReservations(myReservations);

            const now = new Date();
            const activeReservations = myReservations.filter(r => r.status === 'active');
            const upcomingReservations = activeReservations.filter(r => new Date(r.start_time) > now);

            setStats({
                totalResources: allResources.length,
                availableResources: availableResources.length,
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
            <div className="min-h-screen bg-gray-50">
                <header className="border-b bg-white">
                    <div className="container mx-auto flex h-16 items-center justify-between px-4">
                        <Skeleton className="h-8 w-48" />
                        <Skeleton className="h-10 w-10 rounded-full" />
                    </div>
                </header>
                <main className="container mx-auto p-4">
                    <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
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
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="sticky top-0 z-50 border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
                <div className="container mx-auto flex h-16 items-center justify-between px-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
                            <Calendar className="h-5 w-5 text-white" />
                        </div>
                        <span className="text-lg font-semibold">Resource Reserver</span>
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
                                        <AvatarFallback className="bg-blue-600 text-white">
                                            {user?.username?.charAt(0).toUpperCase() || 'U'}
                                        </AvatarFallback>
                                    </Avatar>
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent className="w-56" align="end" side="bottom">
                                <div className="flex items-center gap-2 p-2">
                                    <Avatar className="h-8 w-8">
                                        <AvatarFallback className="bg-blue-600 text-white text-xs">
                                            {user?.username?.charAt(0).toUpperCase() || 'U'}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="flex flex-col">
                                        <span className="text-sm font-medium">{user?.username}</span>
                                        <span className="text-xs text-gray-500">
                                            {user?.mfa_enabled ? '🔒 MFA enabled' : '⚠️ MFA disabled'}
                                        </span>
                                    </div>
                                </div>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={() => setMfaDialogOpen(true)}>
                                    <Settings className="mr-2 h-4 w-4" />
                                    Security Settings
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
            <main className="container mx-auto p-4">
                {/* Stats Grid */}
                <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                    <Card>
                        <CardContent className="p-6">
                            <div className="text-3xl font-bold">{stats.totalResources}</div>
                            <p className="text-sm text-gray-500">Total Resources</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="p-6">
                            <div className="text-3xl font-bold text-green-600">
                                {stats.availableResources}
                            </div>
                            <p className="text-sm text-gray-500">Available Now</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="p-6">
                            <div className="text-3xl font-bold text-blue-600">
                                {stats.activeReservations}
                            </div>
                            <p className="text-sm text-gray-500">Active Bookings</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="p-6">
                            <div className="text-3xl font-bold text-purple-600">
                                {stats.upcomingReservations}
                            </div>
                            <p className="text-sm text-gray-500">Upcoming</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Tabs */}
                <Tabs defaultValue="resources" className="w-full">
                    <TabsList className="mb-4 grid w-full grid-cols-3 lg:w-auto lg:inline-flex">
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
                        <ResourcesTab
                            resources={resources}
                            onRefresh={fetchData}
                        />
                    </TabsContent>

                    <TabsContent value="reservations">
                        <ReservationsTab
                            reservations={reservations}
                            onRefresh={fetchData}
                            showAll
                        />
                    </TabsContent>

                    <TabsContent value="upcoming">
                        <ReservationsTab
                            reservations={upcomingReservations}
                            onRefresh={fetchData}
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
