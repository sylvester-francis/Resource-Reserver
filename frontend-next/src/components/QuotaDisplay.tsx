"use client";

import { useState, useEffect } from 'react';
import { Gauge, Clock, AlertTriangle, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { quotasApi } from '@/lib/api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface QuotaUsage {
  daily_limit: number;
  daily_used: number;
  daily_remaining: number;
  tier: string;
  reset_at?: string;
  rate_limit_per_minute?: number;
}

interface RateLimitConfig {
  tiers: {
    [key: string]: {
      requests_per_minute: number;
      daily_limit: number;
    };
  };
}

export function QuotaDisplay() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [usage, setUsage] = useState<QuotaUsage | null>(null);
  const [config, setConfig] = useState<RateLimitConfig | null>(null);

  useEffect(() => {
    if (open) {
      fetchQuotaData();
    }
  }, [open]);

  const fetchQuotaData = async () => {
    setLoading(true);
    try {
      const [usageRes, configRes] = await Promise.all([
        quotasApi.getMyUsage(),
        quotasApi.getConfig(),
      ]);
      setUsage(usageRes.data);
      setConfig(configRes.data);
    } catch (error) {
      console.error('Failed to fetch quota data:', error);
      toast.error('Failed to load quota information');
    } finally {
      setLoading(false);
    }
  };

  const usagePercent = usage
    ? Math.min((usage.daily_used / usage.daily_limit) * 100, 100)
    : 0;

  const getUsageColor = (percent: number): string => {
    if (percent >= 90) return 'text-destructive';
    if (percent >= 75) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getProgressColor = (percent: number): string => {
    if (percent >= 90) return 'bg-destructive';
    if (percent >= 75) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const formatTimeUntilReset = (resetAt?: string): string => {
    if (!resetAt) return 'tomorrow';
    const reset = new Date(resetAt);
    const now = new Date();
    const diff = reset.getTime() - now.getTime();

    if (diff <= 0) return 'soon';

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2">
          <Gauge className="h-4 w-4" />
          Usage
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Gauge className="h-5 w-5" />
            API Usage & Quotas
          </DialogTitle>
          <DialogDescription>
            Your current API usage and rate limits
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : usage ? (
          <div className="space-y-6 py-4">
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Daily API Calls</CardTitle>
                  <Badge variant="outline">{usage.tier}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Used today</span>
                    <span className={cn("font-medium", getUsageColor(usagePercent))}>
                      {usage.daily_used} / {usage.daily_limit}
                    </span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn("h-full transition-all", getProgressColor(usagePercent))}
                      style={{ width: `${usagePercent}%` }}
                    />
                  </div>
                </div>

                {usagePercent >= 75 && (
                  <div className="flex items-center gap-2 p-2 rounded-md bg-yellow-500/10 text-yellow-600 dark:text-yellow-400">
                    <AlertTriangle className="h-4 w-4" />
                    <span className="text-xs">
                      {usagePercent >= 90
                        ? 'You are close to your daily limit!'
                        : 'You are approaching your daily limit'}
                    </span>
                  </div>
                )}

                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Resets in
                  </span>
                  <span className="font-medium">
                    {formatTimeUntilReset(usage.reset_at)}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Rate Limits</CardTitle>
                <CardDescription>
                  Maximum requests per time window
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Per minute</span>
                    <span className="font-medium">
                      {usage.rate_limit_per_minute ||
                        config?.tiers?.[usage.tier]?.requests_per_minute ||
                        'N/A'}{' '}
                      requests
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Per day</span>
                    <span className="font-medium">
                      {usage.daily_limit} requests
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {config?.tiers && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Available Tiers</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(config.tiers).map(([tier, limits]) => (
                      <div
                        key={tier}
                        className={cn(
                          "flex items-center justify-between p-2 rounded-md text-sm",
                          tier === usage.tier
                            ? "bg-primary/10 border border-primary/20"
                            : "bg-muted/50"
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-medium capitalize">{tier}</span>
                          {tier === usage.tier && (
                            <Badge variant="secondary" className="text-xs">
                              Current
                            </Badge>
                          )}
                        </div>
                        <span className="text-muted-foreground text-xs">
                          {limits.requests_per_minute}/min, {limits.daily_limit}/day
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            Unable to load quota information
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
