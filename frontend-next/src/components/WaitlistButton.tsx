"use client";

import { useState } from 'react';
import { Clock, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { waitlistApi } from '@/lib/api';
import { toast } from 'sonner';

interface WaitlistButtonProps {
  resourceId: number;
  resourceName: string;
  desiredStart: string;
  desiredEnd: string;
  onJoined?: () => void;
  disabled?: boolean;
}

export function WaitlistButton({
  resourceId,
  resourceName,
  desiredStart,
  desiredEnd,
  onJoined,
  disabled = false,
}: WaitlistButtonProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [flexibleTime, setFlexibleTime] = useState(false);

  const handleJoinWaitlist = async () => {
    setLoading(true);
    try {
      await waitlistApi.join({
        resource_id: resourceId,
        desired_start: desiredStart,
        desired_end: desiredEnd,
        flexible_time: flexibleTime,
      });
      toast.success('Joined waitlist', {
        description: `You'll be notified when ${resourceName} becomes available.`,
      });
      setOpen(false);
      onJoined?.();
    } catch (error) {
      toast.error('Failed to join waitlist', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          className="gap-2"
        >
          <Clock className="h-4 w-4" />
          Join Waitlist
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Join Waitlist</DialogTitle>
          <DialogDescription>
            Get notified when {resourceName} becomes available for your desired time slot.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              <strong>Resource:</strong> {resourceName}
            </p>
            <p className="text-sm text-muted-foreground">
              <strong>Time:</strong>{' '}
              {new Date(desiredStart).toLocaleString()} -{' '}
              {new Date(desiredEnd).toLocaleTimeString()}
            </p>
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="flexible-time">Flexible Time</Label>
              <p className="text-xs text-muted-foreground">
                Accept similar time slots if exact match isn&apos;t available
              </p>
            </div>
            <Switch
              id="flexible-time"
              checked={flexibleTime}
              onCheckedChange={setFlexibleTime}
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button onClick={handleJoinWaitlist} disabled={loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Join Waitlist
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
