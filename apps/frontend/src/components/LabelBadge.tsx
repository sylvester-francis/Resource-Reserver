/**
 * Label Badge component for displaying labels with color coding.
 */

'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface LabelData {
    id: number;
    category: string;
    value: string;
    color: string;
    description?: string | null;
    full_name: string;
    resource_count?: number;
}

interface LabelBadgeProps {
    label: LabelData;
    size?: 'sm' | 'md' | 'lg';
    showCategory?: boolean;
    onRemove?: () => void;
    onClick?: () => void;
    className?: string;
}

export function LabelBadge({
    label,
    size = 'md',
    showCategory = true,
    onRemove,
    onClick,
    className,
}: LabelBadgeProps) {
    const sizeClasses = {
        sm: 'text-xs px-1.5 py-0.5',
        md: 'text-xs px-2 py-0.5',
        lg: 'text-sm px-2.5 py-1',
    };

    // Calculate text color based on background brightness
    const getContrastColor = (hexColor: string): string => {
        const hex = hexColor.replace('#', '');
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
        return brightness > 128 ? '#1f2937' : '#ffffff';
    };

    return (
        <span
            className={cn(
                'inline-flex items-center gap-1 rounded-full font-medium transition-colors',
                sizeClasses[size],
                onClick && 'cursor-pointer hover:opacity-80',
                className
            )}
            style={{
                backgroundColor: label.color,
                color: getContrastColor(label.color),
            }}
            onClick={onClick}
            title={label.description || undefined}
        >
            {showCategory && (
                <span className="opacity-70">{label.category}:</span>
            )}
            <span>{label.value}</span>
            {onRemove && (
                <button
                    type="button"
                    onClick={(e) => {
                        e.stopPropagation();
                        onRemove();
                    }}
                    className="ml-0.5 rounded-full p-0.5 hover:bg-black/10"
                    aria-label={`Remove ${label.full_name}`}
                >
                    <svg
                        className="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M6 18L18 6M6 6l12 12"
                        />
                    </svg>
                </button>
            )}
        </span>
    );
}

interface LabelBadgeListProps {
    labels: LabelData[];
    maxDisplay?: number;
    size?: 'sm' | 'md' | 'lg';
    showCategory?: boolean;
    onRemove?: (label: LabelData) => void;
    className?: string;
}

export function LabelBadgeList({
    labels,
    maxDisplay = 3,
    size = 'sm',
    showCategory = false,
    onRemove,
    className,
}: LabelBadgeListProps) {
    const displayedLabels = labels.slice(0, maxDisplay);
    const remainingCount = labels.length - maxDisplay;

    return (
        <div className={cn('flex flex-wrap items-center gap-1', className)}>
            {displayedLabels.map((label) => (
                <LabelBadge
                    key={label.id}
                    label={label}
                    size={size}
                    showCategory={showCategory}
                    onRemove={onRemove ? () => onRemove(label) : undefined}
                />
            ))}
            {remainingCount > 0 && (
                <span
                    className="text-xs text-muted-foreground cursor-help"
                    title={labels
                        .slice(maxDisplay)
                        .map((l) => l.full_name)
                        .join(', ')}
                >
                    +{remainingCount} more
                </span>
            )}
        </div>
    );
}
