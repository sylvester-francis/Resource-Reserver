import { format } from 'date-fns';

export const formatDateTime = (
    value: string | Date | null | undefined,
    fallback = 'N/A',
) => {
    if (!value) return fallback;
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return fallback;
    return format(date, 'MMM d, yyyy h:mm a');
};

export const formatShortDay = (
    value: string | Date | null | undefined,
    fallback = 'Unknown date',
) => {
    if (!value) return fallback;
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return fallback;
    return format(date, 'EEE, MMM d');
};

export const formatTime = (
    value: string | Date | null | undefined,
    fallback = 'N/A',
) => {
    if (!value) return fallback;
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return fallback;
    return format(date, 'h:mm a');
};

export const formatDateKey = (
    value: string | Date | null | undefined,
    fallback = 'unknown',
) => {
    if (!value) return fallback;
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return fallback;
    return format(date, 'yyyy-MM-dd');
};
