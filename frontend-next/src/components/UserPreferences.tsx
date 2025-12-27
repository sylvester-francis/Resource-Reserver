"use client";

import { useState, useEffect } from 'react';
import { Settings, Bell, Loader2, Save } from 'lucide-react';

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
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { userPreferencesApi } from '@/lib/api';
import { toast } from 'sonner';

interface UserPreferencesData {
  email_notifications: boolean;
  reminder_hours: number;
}

export function UserPreferences() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [preferences, setPreferences] = useState<UserPreferencesData>({
    email_notifications: true,
    reminder_hours: 24,
  });
  const [hasChanges, setHasChanges] = useState(false);
  const [originalPreferences, setOriginalPreferences] = useState<UserPreferencesData | null>(null);

  useEffect(() => {
    if (open) {
      fetchPreferences();
    }
  }, [open]);

  useEffect(() => {
    if (originalPreferences) {
      setHasChanges(
        preferences.email_notifications !== originalPreferences.email_notifications ||
        preferences.reminder_hours !== originalPreferences.reminder_hours
      );
    }
  }, [preferences, originalPreferences]);

  const fetchPreferences = async () => {
    setLoading(true);
    try {
      const response = await userPreferencesApi.get();
      const data = {
        email_notifications: response.data.email_notifications ?? true,
        reminder_hours: response.data.reminder_hours ?? 24,
      };
      setPreferences(data);
      setOriginalPreferences(data);
    } catch (error) {
      console.error('Failed to fetch preferences:', error);
      toast.error('Failed to load preferences');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await userPreferencesApi.update(preferences);
      setOriginalPreferences(preferences);
      toast.success('Preferences saved');
      setOpen(false);
    } catch (error) {
      toast.error('Failed to save preferences', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setSaving(false);
    }
  };

  const reminderOptions = [
    { value: '1', label: '1 hour before' },
    { value: '2', label: '2 hours before' },
    { value: '4', label: '4 hours before' },
    { value: '12', label: '12 hours before' },
    { value: '24', label: '1 day before' },
    { value: '48', label: '2 days before' },
    { value: '72', label: '3 days before' },
  ];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2">
          <Settings className="h-4 w-4" />
          Preferences
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle>User Preferences</DialogTitle>
          <DialogDescription>
            Configure your notification and reminder settings.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-6 py-4">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4" />
                  <CardTitle className="text-base">Email Notifications</CardTitle>
                </div>
                <CardDescription>
                  Receive email updates about your reservations.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="email-notifications">Enable Notifications</Label>
                    <p className="text-xs text-muted-foreground">
                      Get confirmations and updates via email
                    </p>
                  </div>
                  <Switch
                    id="email-notifications"
                    checked={preferences.email_notifications}
                    onCheckedChange={(checked) =>
                      setPreferences((prev) => ({ ...prev, email_notifications: checked }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="reminder-hours">Reminder Timing</Label>
                  <Select
                    value={String(preferences.reminder_hours)}
                    onValueChange={(value) =>
                      setPreferences((prev) => ({ ...prev, reminder_hours: parseInt(value) }))
                    }
                    disabled={!preferences.email_notifications}
                  >
                    <SelectTrigger id="reminder-hours">
                      <SelectValue placeholder="Select reminder time" />
                    </SelectTrigger>
                    <SelectContent>
                      {reminderOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    When to receive reminder emails before your reservations
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving || !hasChanges}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
