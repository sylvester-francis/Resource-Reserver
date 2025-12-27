/**
 * Calendar Export component.
 */

"use client";

import { useState, useEffect } from 'react';
import { Calendar, Copy, Download, RefreshCw, Check, ExternalLink, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { calendarApi, API_HOST } from '@/lib/api';
import { toast } from 'sonner';

interface CalendarExportProps {
  reservationId?: number;
}

export function CalendarExport({ reservationId }: CalendarExportProps) {
  const [open, setOpen] = useState(false);
  const [subscriptionUrl, setSubscriptionUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (open && !subscriptionUrl) {
      fetchSubscriptionUrl();
    }
  }, [open, subscriptionUrl]);

  const fetchSubscriptionUrl = async () => {
    setLoading(true);
    try {
      const response = await calendarApi.getSubscriptionUrl();
      const url = response.data.url;
      if (url) {
        // Use absolute URL as-is; fall back to prefixing API_HOST for relative paths
        setSubscriptionUrl(url.startsWith('http') ? url : `${API_HOST}${url}`);
      }
    } catch (error) {
      console.error('Failed to fetch subscription URL:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateToken = async () => {
    setRegenerating(true);
    try {
      const response = await calendarApi.regenerateToken();
      const url = response.data.url;
      if (url) {
        setSubscriptionUrl(url.startsWith('http') ? url : `${API_HOST}${url}`);
        toast.success('Calendar token regenerated', {
          description: 'Your old subscription URL will no longer work.',
        });
      }
    } catch (error) {
      toast.error('Failed to regenerate token', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setRegenerating(false);
    }
  };

  const handleCopyUrl = async () => {
    if (!subscriptionUrl) return;
    try {
      await navigator.clipboard.writeText(subscriptionUrl);
      setCopied(true);
      toast.success('Copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy to clipboard');
    }
  };

  const handleDownloadReservation = async (id: number) => {
    try {
      const response = await calendarApi.exportReservation(id);
      const blob = new Blob([response.data], { type: 'text/calendar' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reservation-${id}.ics`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Calendar event downloaded');
    } catch (error) {
      toast.error('Failed to download calendar event', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleDownloadFeed = async () => {
    try {
      const response = await calendarApi.getMyFeed();
      const blob = new Blob([response.data], { type: 'text/calendar' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'my-reservations.ics';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Calendar feed downloaded');
    } catch (error) {
      toast.error('Failed to download calendar feed', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  if (reservationId) {
    return (
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={() => handleDownloadReservation(reservationId)}
        title="Download calendar event"
      >
        <Download className="h-4 w-4" />
      </Button>
    );
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Calendar className="h-4 w-4" />
          Calendar
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle>Calendar Integration</DialogTitle>
          <DialogDescription>
            Subscribe to your reservations in your favorite calendar app or download events.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Subscription URL</CardTitle>
              <CardDescription>
                Add this URL to any calendar app to automatically sync your reservations.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {loading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : subscriptionUrl ? (
                <>
                  <div className="flex gap-2">
                    <Input
                      value={subscriptionUrl}
                      readOnly
                      className="font-mono text-xs"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={handleCopyUrl}
                      title="Copy URL"
                    >
                      {copied ? (
                        <Check className="h-4 w-4 text-green-500" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleRegenerateToken}
                      disabled={regenerating}
                      className="gap-2 text-muted-foreground"
                    >
                      {regenerating ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3" />
                      )}
                      Regenerate Token
                    </Button>
                    <span className="text-xs text-muted-foreground">
                      (invalidates old URL)
                    </span>
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Unable to load subscription URL
                </p>
              )}
            </CardContent>
          </Card>

          <Separator />

          <div className="space-y-3">
            <Label className="text-sm font-medium">Quick Add to Calendar</Label>
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant="outline"
                size="sm"
                className="justify-start gap-2"
                onClick={() => {
                  if (subscriptionUrl) {
                    window.open(
                      `https://calendar.google.com/calendar/r?cid=${encodeURIComponent(subscriptionUrl.replace('https://', 'webcal://').replace('http://', 'webcal://'))}`,
                      '_blank'
                    );
                  }
                }}
                disabled={!subscriptionUrl}
              >
                <ExternalLink className="h-4 w-4" />
                Google Calendar
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="justify-start gap-2"
                onClick={() => {
                  if (subscriptionUrl) {
                    window.open(
                      `https://outlook.live.com/calendar/0/addfromweb?url=${encodeURIComponent(subscriptionUrl)}`,
                      '_blank'
                    );
                  }
                }}
                disabled={!subscriptionUrl}
              >
                <ExternalLink className="h-4 w-4" />
                Outlook
              </Button>
            </div>
          </div>

          <Separator />

          <div className="space-y-3">
            <Label className="text-sm font-medium">Download</Label>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadFeed}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Download All Reservations (.ics)
            </Button>
          </div>

          <Card className="bg-muted/50">
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">
                <strong>Tip:</strong> For iOS/macOS, copy the subscription URL and go to Settings {'->'} Calendar {'->'} Accounts {'->'} Add Account {'->'} Other {'->'} Add Subscribed Calendar.
              </p>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
}
