"use client";

import { useMemo } from 'react';

import type { RecurrenceEndType, RecurrenceFrequency, RecurrenceRule } from '@/types';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';

interface RecurrenceSelectorProps {
  enabled: boolean;
  value: RecurrenceRule;
  onChange: (value: RecurrenceRule) => void;
  onToggle: (enabled: boolean) => void;
}

const days = [
  { label: 'Mon', value: 0 },
  { label: 'Tue', value: 1 },
  { label: 'Wed', value: 2 },
  { label: 'Thu', value: 3 },
  { label: 'Fri', value: 4 },
  { label: 'Sat', value: 5 },
  { label: 'Sun', value: 6 },
];

export function RecurrenceSelector({ enabled, value, onChange, onToggle }: RecurrenceSelectorProps) {
  const selectedDays = useMemo(() => new Set(value.days_of_week || []), [value.days_of_week]);

  const updateField = (field: keyof RecurrenceRule, fieldValue: unknown) => {
    onChange({ ...value, [field]: fieldValue });
  };

  const toggleDay = (day: number) => {
    const next = new Set(selectedDays);
    if (next.has(day)) {
      next.delete(day);
    } else {
      next.add(day);
    }
    updateField('days_of_week', Array.from(next));
  };

  return (
    <div className="space-y-3 rounded-lg border p-3">
      <div className="flex items-center justify-between">
        <Label className="font-medium">Repeat</Label>
        <Switch checked={enabled} onCheckedChange={onToggle} />
      </div>

      {enabled && (
        <div className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <Label>Frequency</Label>
              <Select
                value={value.frequency}
                onValueChange={val => updateField('frequency', val as RecurrenceFrequency)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select frequency" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Interval</Label>
              <Input
                type="number"
                min={1}
                value={value.interval ?? 1}
                onChange={e => updateField('interval', Number(e.target.value) || 1)}
              />
            </div>
          </div>

          {value.frequency === 'weekly' && (
            <div className="space-y-2">
              <Label>Days of week</Label>
              <div className="flex flex-wrap gap-2">
                {days.map(day => (
                  <button
                    key={day.value}
                    type="button"
                    className={`rounded-full border px-3 py-1 text-sm ${
                      selectedDays.has(day.value)
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border text-muted-foreground'
                    }`}
                    onClick={() => toggleDay(day.value)}
                  >
                    {day.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <Label>Ends</Label>
              <Select
                value={value.end_type || 'after_count'}
                onValueChange={val => updateField('end_type', val as RecurrenceEndType)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select end" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="never">Never</SelectItem>
                  <SelectItem value="after_count">After #</SelectItem>
                  <SelectItem value="on_date">On date</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {value.end_type === 'after_count' && (
              <div className="space-y-1">
                <Label>Occurrences</Label>
                <Input
                  type="number"
                  min={1}
                  max={100}
                  value={value.occurrence_count ?? 5}
                  onChange={e => updateField('occurrence_count', Number(e.target.value) || 1)}
                />
              </div>
            )}
            {value.end_type === 'on_date' && (
              <div className="space-y-1">
                <Label>End date</Label>
                <Input
                  type="date"
                  value={value.end_date ?? ''}
                  onChange={e => updateField('end_date', e.target.value)}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
