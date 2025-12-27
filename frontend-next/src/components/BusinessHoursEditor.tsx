"use client";

import { useState, useEffect, useCallback } from 'react';
import { Clock, Save, Loader2, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
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
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { businessHoursApi } from '@/lib/api';
import { toast } from 'sonner';

interface BusinessHour {
  day_of_week: number;
  open_time: string;
  close_time: string;
  is_closed: boolean;
}

interface BlackoutDate {
  id: number;
  date: string;
  reason?: string;
  resource_id?: number;
}

interface BusinessHoursEditorProps {
  resourceId?: number;
  resourceName?: string;
  isAdmin?: boolean;
}

const DAYS = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

const PRESETS = {
  '9-5': {
    label: '9 AM - 5 PM (Weekdays)',
    hours: DAYS.map((_, i) => ({
      day_of_week: i,
      open_time: '09:00',
      close_time: '17:00',
      is_closed: i >= 5,
    })),
  },
  '8-6': {
    label: '8 AM - 6 PM (Weekdays)',
    hours: DAYS.map((_, i) => ({
      day_of_week: i,
      open_time: '08:00',
      close_time: '18:00',
      is_closed: i >= 5,
    })),
  },
  '24/7': {
    label: '24/7',
    hours: DAYS.map((_, i) => ({
      day_of_week: i,
      open_time: '00:00',
      close_time: '23:59',
      is_closed: false,
    })),
  },
};

export function BusinessHoursEditor({
  resourceId,
  resourceName,
  isAdmin = false,
}: BusinessHoursEditorProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hours, setHours] = useState<BusinessHour[]>([]);
  const [blackoutDates, setBlackoutDates] = useState<BlackoutDate[]>([]);
  const [newBlackoutDate, setNewBlackoutDate] = useState('');
  const [newBlackoutReason, setNewBlackoutReason] = useState('');

  const fetchBusinessHours = useCallback(async () => {
    setLoading(true);
    try {
      const response = resourceId
        ? await businessHoursApi.getResourceHours(resourceId)
        : await businessHoursApi.getGlobalHours();

      if (response.data && response.data.length > 0) {
        setHours(response.data);
      } else {
        setHours(PRESETS['9-5'].hours);
      }
    } catch (error) {
      console.error('Failed to fetch business hours:', error);
      setHours(PRESETS['9-5'].hours);
    } finally {
      setLoading(false);
    }
  }, [resourceId]);

  const fetchBlackoutDates = useCallback(async () => {
    try {
      const response = await businessHoursApi.getBlackoutDates(resourceId);
      setBlackoutDates(response.data || []);
    } catch (error) {
      console.error('Failed to fetch blackout dates:', error);
    }
  }, [resourceId]);

  useEffect(() => {
    if (open) {
      fetchBusinessHours();
      fetchBlackoutDates();
    }
  }, [open, fetchBusinessHours, fetchBlackoutDates]);

  const handleSave = async () => {
    setSaving(true);
    try {
      if (resourceId) {
        await businessHoursApi.setResourceHours(resourceId, hours);
      } else {
        await businessHoursApi.setGlobalHours(hours);
      }
      toast.success('Business hours saved');
      setOpen(false);
    } catch (error) {
      toast.error('Failed to save business hours', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleApplyPreset = (preset: keyof typeof PRESETS) => {
    setHours(PRESETS[preset].hours);
  };

  const handleDayChange = (dayIndex: number, field: keyof BusinessHour, value: string | boolean) => {
    setHours(prev => prev.map(h =>
      h.day_of_week === dayIndex
        ? { ...h, [field]: value }
        : h
    ));
  };

  const handleAddBlackoutDate = async () => {
    if (!newBlackoutDate) return;

    try {
      await businessHoursApi.createBlackoutDate({
        date: newBlackoutDate,
        reason: newBlackoutReason || undefined,
        resource_id: resourceId,
      });
      toast.success('Blackout date added');
      setNewBlackoutDate('');
      setNewBlackoutReason('');
      fetchBlackoutDates();
    } catch (error) {
      toast.error('Failed to add blackout date', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleDeleteBlackoutDate = async (blackoutId: number) => {
    try {
      await businessHoursApi.deleteBlackoutDate(blackoutId);
      toast.success('Blackout date removed');
      fetchBlackoutDates();
    } catch (error) {
      toast.error('Failed to remove blackout date', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  if (!isAdmin) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Clock className="h-4 w-4" />
          Business Hours
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {resourceId ? `Business Hours: ${resourceName}` : 'Global Business Hours'}
          </DialogTitle>
          <DialogDescription>
            Configure when {resourceId ? 'this resource' : 'resources'} can be booked.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-6 py-4">
            <div className="flex flex-wrap gap-2">
              <Label className="text-sm font-medium">Quick Presets:</Label>
              {Object.entries(PRESETS).map(([key, preset]) => (
                <Button
                  key={key}
                  variant="outline"
                  size="sm"
                  onClick={() => handleApplyPreset(key as keyof typeof PRESETS)}
                >
                  {preset.label}
                </Button>
              ))}
            </div>

            <Separator />

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Weekly Schedule</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {hours.map((hour) => (
                  <div key={hour.day_of_week} className="flex items-center gap-3">
                    <span className="w-24 text-sm font-medium">
                      {DAYS[hour.day_of_week]}
                    </span>
                    <Switch
                      checked={!hour.is_closed}
                      onCheckedChange={(checked) =>
                        handleDayChange(hour.day_of_week, 'is_closed', !checked)
                      }
                    />
                    {!hour.is_closed && (
                      <>
                        <Input
                          type="time"
                          value={hour.open_time}
                          onChange={(e) =>
                            handleDayChange(hour.day_of_week, 'open_time', e.target.value)
                          }
                          className="w-28"
                        />
                        <span className="text-muted-foreground">to</span>
                        <Input
                          type="time"
                          value={hour.close_time}
                          onChange={(e) =>
                            handleDayChange(hour.day_of_week, 'close_time', e.target.value)
                          }
                          className="w-28"
                        />
                      </>
                    )}
                    {hour.is_closed && (
                      <span className="text-sm text-muted-foreground">Closed</span>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Blackout Dates</CardTitle>
                <CardDescription>
                  Days when the resource is unavailable (holidays, maintenance, etc.)
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Input
                    type="date"
                    value={newBlackoutDate}
                    onChange={(e) => setNewBlackoutDate(e.target.value)}
                    className="w-40"
                  />
                  <Input
                    placeholder="Reason (optional)"
                    value={newBlackoutReason}
                    onChange={(e) => setNewBlackoutReason(e.target.value)}
                    className="flex-1"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleAddBlackoutDate}
                    disabled={!newBlackoutDate}
                  >
                    Add
                  </Button>
                </div>

                {blackoutDates.length > 0 && (
                  <div className="space-y-2">
                    {blackoutDates.map((blackout) => (
                      <div
                        key={blackout.id}
                        className="flex items-center justify-between p-2 rounded-md bg-muted/50"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium">
                            {new Date(blackout.date).toLocaleDateString()}
                          </span>
                          {blackout.reason && (
                            <span className="text-xs text-muted-foreground">
                              {blackout.reason}
                            </span>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => handleDeleteBlackoutDate(blackout.id)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving || loading}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
