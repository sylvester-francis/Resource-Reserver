"use client";

import { useState, useEffect, useCallback } from 'react';
import { Loader2, Clock } from 'lucide-react';

import { businessHoursApi } from '@/lib/api';
import { cn } from '@/lib/utils';

interface TimeSlot {
  start: string;
  end: string;
  available: boolean;
}

interface TimeSlotPickerProps {
  resourceId: number;
  date: Date;
  onSelectSlot?: (start: Date, end: Date) => void;
  selectedStart?: Date | null;
  selectedEnd?: Date | null;
}

export function TimeSlotPicker({
  resourceId,
  date,
  onSelectSlot,
  selectedStart,
  selectedEnd,
}: TimeSlotPickerProps) {
  const [loading, setLoading] = useState(false);
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [selecting, setSelecting] = useState(false);
  const [selectionStart, setSelectionStart] = useState<number | null>(null);
  const [selectionEnd, setSelectionEnd] = useState<number | null>(null);

  const fetchSlots = useCallback(async () => {
    setLoading(true);
    try {
      const dateStr = date.toISOString().split('T')[0];
      const response = await businessHoursApi.getAvailableSlots(resourceId, dateStr);
      setSlots(response.data?.slots || []);
    } catch (error) {
      console.error('Failed to fetch available slots:', error);
      setSlots([]);
    } finally {
      setLoading(false);
    }
  }, [resourceId, date]);

  useEffect(() => {
    if (resourceId && date) {
      fetchSlots();
    }
  }, [resourceId, date, fetchSlots]);

  const handleSlotClick = (index: number) => {
    const slot = slots[index];
    if (!slot.available) return;

    if (!selecting || selectionStart === null) {
      setSelecting(true);
      setSelectionStart(index);
      setSelectionEnd(index);
    } else {
      const start = Math.min(selectionStart, index);
      const end = Math.max(selectionStart, index);

      const allAvailable = slots.slice(start, end + 1).every(s => s.available);
      if (!allAvailable) {
        setSelecting(false);
        setSelectionStart(null);
        setSelectionEnd(null);
        return;
      }

      setSelectionEnd(index);
      setSelecting(false);

      if (onSelectSlot) {
        const startSlot = slots[start];
        const endSlot = slots[end];
        onSelectSlot(
          new Date(startSlot.start),
          new Date(endSlot.end)
        );
      }
    }
  };

  const handleSlotHover = (index: number) => {
    if (selecting && selectionStart !== null) {
      const slot = slots[index];
      if (slot.available) {
        const start = Math.min(selectionStart, index);
        const end = Math.max(selectionStart, index);
        const allAvailable = slots.slice(start, end + 1).every(s => s.available);
        if (allAvailable) {
          setSelectionEnd(index);
        }
      }
    }
  };

  const isSlotSelected = (index: number): boolean => {
    if (selectionStart === null) return false;
    const end = selectionEnd ?? selectionStart;
    const min = Math.min(selectionStart, end);
    const max = Math.max(selectionStart, end);
    return index >= min && index <= max;
  };

  const isSlotInRange = (slot: TimeSlot): boolean => {
    if (!selectedStart || !selectedEnd) return false;
    const slotStart = new Date(slot.start);
    const slotEnd = new Date(slot.end);
    return slotStart >= selectedStart && slotEnd <= selectedEnd;
  };

  const formatTime = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (slots.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No available time slots for this date</p>
      </div>
    );
  }

  const morningSlots = slots.filter(s => {
    const hour = new Date(s.start).getHours();
    return hour < 12;
  });

  const afternoonSlots = slots.filter(s => {
    const hour = new Date(s.start).getHours();
    return hour >= 12 && hour < 17;
  });

  const eveningSlots = slots.filter(s => {
    const hour = new Date(s.start).getHours();
    return hour >= 17;
  });

  const renderSlotGroup = (groupSlots: TimeSlot[], label: string) => {
    if (groupSlots.length === 0) return null;

    return (
      <div className="space-y-2">
        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {label}
        </h4>
        <div className="grid grid-cols-4 sm:grid-cols-6 gap-1">
          {groupSlots.map((slot) => {
            const globalIndex = slots.indexOf(slot);
            const isSelected = isSlotSelected(globalIndex) || isSlotInRange(slot);
            return (
              <button
                key={slot.start}
                onClick={() => handleSlotClick(globalIndex)}
                onMouseEnter={() => handleSlotHover(globalIndex)}
                disabled={!slot.available}
                className={cn(
                  "px-2 py-1.5 text-xs rounded-md transition-colors",
                  "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
                  slot.available
                    ? isSelected
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted hover:bg-muted/80 text-foreground"
                    : "bg-muted/40 text-muted-foreground/50 cursor-not-allowed line-through"
                )}
              >
                {formatTime(slot.start)}
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  const selectedDuration = () => {
    if (selectionStart === null || selectionEnd === null) return null;
    const start = Math.min(selectionStart, selectionEnd);
    const end = Math.max(selectionStart, selectionEnd);
    const startTime = new Date(slots[start].start);
    const endTime = new Date(slots[end].end);
    const durationMs = endTime.getTime() - startTime.getTime();
    const durationMins = Math.round(durationMs / (1000 * 60));

    if (durationMins < 60) {
      return `${durationMins} min`;
    } else {
      const hours = Math.floor(durationMins / 60);
      const mins = durationMins % 60;
      return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">
          {date.toLocaleDateString(undefined, {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
          })}
        </p>
        {selecting && (
          <span className="text-xs text-muted-foreground">
            Click another slot to complete selection
          </span>
        )}
      </div>

      <div className="space-y-4">
        {renderSlotGroup(morningSlots, 'Morning')}
        {renderSlotGroup(afternoonSlots, 'Afternoon')}
        {renderSlotGroup(eveningSlots, 'Evening')}
      </div>

      {selectionStart !== null && selectionEnd !== null && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-primary/10 text-primary">
          <div className="text-sm">
            <span className="font-medium">
              {formatTime(slots[Math.min(selectionStart, selectionEnd)].start)}
            </span>
            <span className="mx-2">-</span>
            <span className="font-medium">
              {formatTime(slots[Math.max(selectionStart, selectionEnd)].end)}
            </span>
          </div>
          <span className="text-sm font-medium">{selectedDuration()}</span>
        </div>
      )}

      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-muted" />
          <span>Available</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-primary" />
          <span>Selected</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-muted/40" />
          <span>Unavailable</span>
        </div>
      </div>
    </div>
  );
}
