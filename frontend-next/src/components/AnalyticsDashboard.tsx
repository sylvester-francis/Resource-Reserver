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
  total_hours: number;
  booked_hours: number;
  utilization_percent: number;
}

interface PopularResource {
  resource_id: number;
  resource_name: string;
  reservation_count: number;
  total_hours: number;
}

interface PeakTimeData {
  hourly: { hour: number; count: number }[];
  daily: { day: number; count: number }[];
}

interface UserPattern {
  user_id: number;
  username: string;
  reservation_count: number;
  total_hours: number;
  avg_duration_hours: number;
}

interface DashboardData {
  utilization: UtilizationData[];
  popular_resources: PopularResource[];
  peak_times: PeakTimeData;
  user_patterns: UserPattern[];
  total_reservations: number;
  total_hours_booked: number;
  avg_utilization: number;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export function AnalyticsDashboard() {
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [data, setData] = useState<DashboardData | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const response = await analyticsApi.getDashboard({ days });
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      toast.error('Failed to load analytics');
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

  const maxHourlyCount = Math.max(...(data.peak_times?.hourly?.map(h => h.count) || [1]));
  const maxDailyCount = Math.max(...(data.peak_times?.daily?.map(d => d.count) || [1]));

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold">Analytics</h2>
          <p className="text-sm text-muted-foreground">
            Resource utilization and booking insights
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
                <p className="text-2xl font-semibold">{data.total_reservations}</p>
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
                <p className="text-sm text-muted-foreground">Hours Booked</p>
                <p className="text-2xl font-semibold">{data.total_hours_booked?.toFixed(1) || 0}</p>
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
                <p className="text-2xl font-semibold">{data.avg_utilization?.toFixed(1) || 0}%</p>
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
                <p className="text-sm text-muted-foreground">Active Users</p>
                <p className="text-2xl font-semibold">{data.user_patterns?.length || 0}</p>
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
              {data.popular_resources?.slice(0, 5).map((resource, index) => (
                <div key={resource.resource_id} className="flex items-center gap-4">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium">
                    {index + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{resource.resource_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {resource.reservation_count} reservations
                    </p>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {resource.total_hours?.toFixed(1)}h
                  </span>
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
                {data.peak_times?.hourly?.slice(0, 12).map(({ hour, count }) => (
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
                {data.peak_times?.daily?.map(({ day, count }) => (
                  <div key={day} className="flex items-center gap-2">
                    <span className="w-12 text-xs text-muted-foreground">
                      {DAYS[day] || day}
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
                  <th className="text-right py-2 font-medium">Total Hours</th>
                  <th className="text-right py-2 font-medium">Avg Duration</th>
                </tr>
              </thead>
              <tbody>
                {data.user_patterns?.slice(0, 10).map((user) => (
                  <tr key={user.user_id} className="border-b border-border/50">
                    <td className="py-2">{user.username}</td>
                    <td className="text-right py-2">{user.reservation_count}</td>
                    <td className="text-right py-2">{user.total_hours?.toFixed(1)}h</td>
                    <td className="text-right py-2">{user.avg_duration_hours?.toFixed(1)}h</td>
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
