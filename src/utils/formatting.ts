export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString();
}

export function formatTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleTimeString();
}

export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString();
}

export function getTimeUntil(date: Date | string): string {
  const startTime = typeof date === 'string' ? new Date(date) : date;
  const timeUntil = startTime.getTime() - new Date().getTime();
  const hoursUntil = Math.floor(timeUntil / (1000 * 60 * 60));
  const daysUntil = Math.floor(hoursUntil / 24);

  if (daysUntil > 0) {
    return `in ${daysUntil} day${daysUntil > 1 ? 's' : ''}`;
  } else if (hoursUntil > 0) {
    return `in ${hoursUntil} hour${hoursUntil > 1 ? 's' : ''}`;
  } else {
    return 'starting soon';
  }
}

export function padResourceId(id: number): string {
  return `#${id.toString().padStart(3, '0')}`;
}

export function capitalizeFirst(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}