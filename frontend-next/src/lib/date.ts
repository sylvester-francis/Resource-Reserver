import { format } from 'date-fns';

const toDate = (value: string | Date | null | undefined) => {
    if (!value) return null;
    if (value instanceof Date) return value;
    if (typeof value !== 'string') return null;

    const direct = new Date(value);
    if (!Number.isNaN(direct.getTime())) return direct;

    const candidate =
        value.includes(' ') && !value.includes('T') ? value.replace(' ', 'T') : value;
    const parsed = new Date(candidate);
    if (!Number.isNaN(parsed.getTime())) return parsed;

    return null;
};

export const formatDateTime = (
    value: string | Date | null | undefined,
    fallback = 'N/A',
) => {
    if (!value) return fallback;
    const date = toDate(value);
    if (!date) return fallback;
    return format(date, 'MMM d, yyyy h:mm a');
};

export const formatShortDay = (
    value: string | Date | null | undefined,
    fallback = 'Unknown date',
) => {
    if (!value) return fallback;
    const date = toDate(value);
    if (!date) return fallback;
    return format(date, 'EEE, MMM d');
};

export const formatTime = (
    value: string | Date | null | undefined,
    fallback = 'N/A',
) => {
    if (!value) return fallback;
    const date = toDate(value);
    if (!date) return fallback;
    return format(date, 'h:mm a');
};

export const formatDateKey = (
    value: string | Date | null | undefined,
    fallback = 'unknown',
) => {
    if (!value) return fallback;
    const date = toDate(value);
    if (!date) return fallback;
    return format(date, 'yyyy-MM-dd');
};
