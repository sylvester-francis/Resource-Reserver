/**
 * Analytics Dashboard component.
 */

"use client";

import { useState, useEffect, useCallback } from 'react';
import {
  BarChart3,
  TrendingUp,
  Clock,
  Users,
  Download,
  Loader2,
  CalendarDays,
  Percent
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { analyticsApi } from '@/lib/api';
import { toast } from 'sonner';

interface UtilizationData {
  resource_id: number;
  resource_name: string;
  total_hours_available: number;
  booked_hours: number;
  utilization_percent: number;
}

interface PopularResource {
  resource_id: number;
  resource_name: string;
  reservation_count: number;
  rank: number;
}

interface HourlyData {
  hour: number;
  count: number;
}

interface DailyData {
  day: string;
  day_number: number;
  count: number;
}

interface PeakTimeData {
  hourly_distribution: HourlyData[];
  daily_distribution: DailyData[];
  peak_hour: number;
  peak_day: string;
}

interface UserPattern {
  user_id: number;
  username: string;
  total_reservations: number;
  cancelled_count: number;
  cancellation_rate: number;
}

interface DashboardOverview {
  total_resources: number;
  total_users: number;
  total_reservations: number;
  active_reservations: number;
  cancelled_reservations: number;
  cancellation_rate: number;
  average_utilization: number;
}

interface DashboardData {
  overview: DashboardOverview;
  utilization: UtilizationData[];
  popular_resources: PopularResource[];
  peak_times: PeakTimeData | null;
  user_patterns: UserPattern[];
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const safeArray = <T,>(value: unknown, fallback: T[] = []): T[] =>
  Array.isArray(value) ? (value as T[]) : fallback;

const normalizePeakTimes = (value: unknown): PeakTimeData | null => {
  if (!value || typeof value !== 'object') return null;
  const v = value as Partial<PeakTimeData>;
  return {
    hourly_distribution: safeArray(v.hourly_distribution, []),
    daily_distribution: safeArray(v.daily_distribution, []),
    peak_hour: typeof v.peak_hour === 'number' ? v.peak_hour : 0,
    peak_day: typeof v.peak_day === 'string' ? v.peak_day : '',
  };
};

export function AnalyticsDashboard() {
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [data, setData] = useState<DashboardData | null>(null);
  const [hadErrors, setHadErrors] = useState(false);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch from multiple endpoints in parallel; tolerate partial failures
      const results = await Promise.allSettled([
        analyticsApi.getDashboard({ days }),
        analyticsApi.getUtilization({ days }),
        analyticsApi.getPopularResources({ days, limit: 10 }),
        analyticsApi.getPeakTimes({ days }),
        analyticsApi.getUserPatterns({ days }),
      ]);

      const [dashboardRes, utilizationRes, popularRes, peakTimesRes, userPatternsRes] = results;

      const getData = <T,>(res: typeof results[number], fallback: T): T =>
        res.status === 'fulfilled' ? (res.value.data as T) : fallback;

      const overview = (getData(dashboardRes, { overview: null }) as { overview: DashboardOverview | null }).overview;
      const utilization = safeArray<UtilizationData>(getData(utilizationRes, []));
      const popularResources = safeArray<PopularResource>(getData(popularRes, []));
      const peakTimes = normalizePeakTimes(getData(peakTimesRes, null));
      const userPatterns = safeArray<UserPattern>(getData(userPatternsRes, []));

      setData({
        overview: overview ?? {
          total_resources: 0,
          total_users: 0,
          total_reservations: 0,
          active_reservations: 0,
          cancelled_reservations: 0,
          cancellation_rate: 0,
          average_utilization: 0,
        },
        utilization,
        popular_resources: popularResources,
        peak_times: peakTimes,
        user_patterns: userPatterns,
      });

      const anyFailures = results.some((r) => r.status === 'rejected');
      setHadErrors(anyFailures);
      if (anyFailures) {
        toast.error('Some analytics panels failed to load. Showing available data.');
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      toast.error('Failed to load analytics');
      setHadErrors(true);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const handleExportUtilization = async () => {
    try {
      const response = await analyticsApi.exportUtilization({ days });
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `utilization-report-${days}days.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Utilization report downloaded');
    } catch (error) {
      toast.error('Failed to download report', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleExportReservations = async () => {
    try {
      const response = await analyticsApi.exportReservations({ days });
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reservations-report-${days}days.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Reservations report downloaded');
    } catch (error) {
      toast.error('Failed to download report', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        Failed to load analytics data
      </div>
    );
  }

  const maxHourlyCount = Math.max(...(data.peak_times?.hourly_distribution?.map(h => h.count) || [1]));
  const maxDailyCount = Math.max(...(data.peak_times?.daily_distribution?.map(d => d.count) || [1]));

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold">Analytics</h2>
          <p className="text-sm text-muted-foreground">
            Resource utilization and booking insights{hadErrors ? ' (partial data shown)' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={String(days)} onValueChange={(v) => setDays(parseInt(v))}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
              <SelectItem value="365">Last year</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-500">
                <CalendarDays className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Reservations</p>
                <p className="text-2xl font-semibold">{data.overview.total_reservations}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-green-500/10 text-green-500">
                <Clock className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Active Reservations</p>
                <p className="text-2xl font-semibold">{data.overview.active_reservations}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-purple-500/10 text-purple-500">
                <Percent className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Avg Utilization</p>
                <p className="text-2xl font-semibold">{data.overview.average_utilization?.toFixed(1) || 0}%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-500/10 text-orange-500">
                <Users className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Users</p>
                <p className="text-2xl font-semibold">{data.overview.total_users}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Popular Resources
                </CardTitle>
                <CardDescription>Most booked resources</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {data.popular_resources?.slice(0, 5).map((resource) => (
                <div key={resource.resource_id} className="flex items-center gap-4">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium">
                    {resource.rank}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{resource.resource_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {resource.reservation_count} reservations
                    </p>
                  </div>
                </div>
              )) || (
                <p className="text-sm text-muted-foreground">No data available</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Resource Utilization
            </CardTitle>
            <CardDescription>Percentage of available time booked</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {data.utilization?.slice(0, 5).map((resource) => (
                <div key={resource.resource_id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium truncate">{resource.resource_name}</span>
                    <span className="text-sm text-muted-foreground">
                      {resource.utilization_percent?.toFixed(1)}%
                    </span>
                  </div>
                  <Progress value={resource.utilization_percent || 0} className="h-2" />
                </div>
              )) || (
                <p className="text-sm text-muted-foreground">No data available</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Peak Usage Times
          </CardTitle>
          <CardDescription>When resources are most frequently booked</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <h4 className="text-sm font-medium mb-3">By Hour</h4>
              <div className="space-y-1">
                {data.peak_times?.hourly_distribution?.slice(0, 12).map(({ hour, count }) => (
                  <div key={hour} className="flex items-center gap-2">
                    <span className="w-12 text-xs text-muted-foreground">
                      {hour.toString().padStart(2, '0')}:00
                    </span>
                    <div className="flex-1 h-4 bg-muted rounded-sm overflow-hidden">
                      <div
                        className="h-full bg-primary/60"
                        style={{ width: `${(count / maxHourlyCount) * 100}%` }}
                      />
                    </div>
                    <span className="w-8 text-xs text-muted-foreground text-right">
                      {count}
                    </span>
                  </div>
                )) || (
                  <p className="text-sm text-muted-foreground">No data</p>
                )}
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium mb-3">By Day</h4>
              <div className="space-y-1">
                {data.peak_times?.daily_distribution?.map(({ day, day_number, count }) => (
                  <div key={day_number} className="flex items-center gap-2">
                    <span className="w-12 text-xs text-muted-foreground">
                      {DAYS[day_number] || day}
                    </span>
                    <div className="flex-1 h-4 bg-muted rounded-sm overflow-hidden">
                      <div
                        className="h-full bg-primary/60"
                        style={{ width: `${(count / maxDailyCount) * 100}%` }}
                      />
                    </div>
                    <span className="w-8 text-xs text-muted-foreground text-right">
                      {count}
                    </span>
                  </div>
                )) || (
                  <p className="text-sm text-muted-foreground">No data</p>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                User Booking Patterns
              </CardTitle>
              <CardDescription>Top users by booking activity</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 font-medium">User</th>
                  <th className="text-right py-2 font-medium">Reservations</th>
                  <th className="text-right py-2 font-medium">Cancelled</th>
                  <th className="text-right py-2 font-medium">Cancel Rate</th>
                </tr>
              </thead>
              <tbody>
                {data.user_patterns?.slice(0, 10).map((user) => (
                  <tr key={user.user_id} className="border-b border-border/50">
                    <td className="py-2">{user.username}</td>
                    <td className="text-right py-2">{user.total_reservations}</td>
                    <td className="text-right py-2">{user.cancelled_count}</td>
                    <td className="text-right py-2">{user.cancellation_rate?.toFixed(1)}%</td>
                  </tr>
                )) || (
                  <tr>
                    <td colSpan={4} className="py-4 text-center text-muted-foreground">
                      No data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Separator />

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={handleExportUtilization} className="gap-2">
          <Download className="h-4 w-4" />
          Export Utilization (CSV)
        </Button>
        <Button variant="outline" size="sm" onClick={handleExportReservations} className="gap-2">
          <Download className="h-4 w-4" />
          Export Reservations (CSV)
        </Button>
      </div>
    </div>
  );
}
