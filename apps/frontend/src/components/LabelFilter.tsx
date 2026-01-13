/**
 * Label Filter component for filtering resources by labels.
 */

'use client';

import * as React from 'react';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Filter, X, ChevronDown, ChevronRight } from 'lucide-react';

import { cn } from '@/lib/utils';
import { labelsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { LabelBadge, type LabelData } from '@/components/LabelBadge';

interface LabelFilterProps {
    selectedLabelIds: number[];
    onChange: (labelIds: number[]) => void;
    className?: string;
}

interface CategoryWithLabels {
    category: string;
    labels: LabelData[];
    isExpanded: boolean;
}

export function LabelFilter({
    selectedLabelIds,
    onChange,
    className,
}: LabelFilterProps) {
    const [categories, setCategories] = useState<CategoryWithLabels[]>([]);
    const [loading, setLoading] = useState(true);
    const [allLabels, setAllLabels] = useState<LabelData[]>([]);

    const fetchLabels = useCallback(async () => {
        setLoading(true);
        try {
            const response = await labelsApi.list({ limit: 100 });
            const labels: LabelData[] = response.data.data || [];
            setAllLabels(labels);

            // Group by category
            const categoryMap: Record<string, LabelData[]> = {};
            labels.forEach((label) => {
                if (!categoryMap[label.category]) {
                    categoryMap[label.category] = [];
                }
                categoryMap[label.category].push(label);
            });

            setCategories(
                Object.entries(categoryMap).map(([category, categoryLabels]) => ({
                    category,
                    labels: categoryLabels,
                    isExpanded: true,
                }))
            );
        } catch (error) {
            console.error('Failed to fetch labels:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchLabels();
    }, [fetchLabels]);

    const toggleCategory = (categoryName: string) => {
        setCategories((prev) =>
            prev.map((cat) =>
                cat.category === categoryName
                    ? { ...cat, isExpanded: !cat.isExpanded }
                    : cat
            )
        );
    };

    const toggleLabel = (labelId: number) => {
        if (selectedLabelIds.includes(labelId)) {
            onChange(selectedLabelIds.filter((id) => id !== labelId));
        } else {
            onChange([...selectedLabelIds, labelId]);
        }
    };

    const clearAll = () => {
        onChange([]);
    };

    const selectedLabels = useMemo(
        () => allLabels.filter((l) => selectedLabelIds.includes(l.id)),
        [allLabels, selectedLabelIds]
    );

    if (loading) {
        return (
            <div className={cn('p-4 text-sm text-muted-foreground', className)}>
                Loading filters...
            </div>
        );
    }

    if (categories.length === 0) {
        return null;
    }

    return (
        <div className={cn('space-y-3', className)}>
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-medium">
                    <Filter className="h-4 w-4" />
                    Filter by Labels
                </div>
                {selectedLabelIds.length > 0 && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={clearAll}
                        className="h-6 px-2 text-xs"
                    >
                        <X className="mr-1 h-3 w-3" />
                        Clear ({selectedLabelIds.length})
                    </Button>
                )}
            </div>

            {/* Selected labels preview */}
            {selectedLabels.length > 0 && (
                <div className="flex flex-wrap gap-1 pb-2 border-b">
                    {selectedLabels.map((label) => (
                        <LabelBadge
                            key={label.id}
                            label={label}
                            size="sm"
                            showCategory={false}
                            onRemove={() => toggleLabel(label.id)}
                        />
                    ))}
                </div>
            )}

            {/* Category accordions */}
            <div className="space-y-2">
                {categories.map(({ category, labels, isExpanded }) => (
                    <div key={category} className="border rounded-lg overflow-hidden">
                        {/* Category header */}
                        <button
                            type="button"
                            onClick={() => toggleCategory(category)}
                            className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium bg-muted/50 hover:bg-muted transition-colors"
                        >
                            <span className="flex items-center gap-2">
                                {isExpanded ? (
                                    <ChevronDown className="h-4 w-4" />
                                ) : (
                                    <ChevronRight className="h-4 w-4" />
                                )}
                                {category}
                            </span>
                            <span className="text-xs text-muted-foreground">
                                {labels.filter((l) => selectedLabelIds.includes(l.id)).length}/
                                {labels.length}
                            </span>
                        </button>

                        {/* Labels */}
                        {isExpanded && (
                            <div className="p-2 space-y-1">
                                {labels.map((label) => {
                                    const isSelected = selectedLabelIds.includes(label.id);
                                    return (
                                        <button
                                            key={label.id}
                                            type="button"
                                            onClick={() => toggleLabel(label.id)}
                                            className={cn(
                                                'w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm transition-colors',
                                                isSelected
                                                    ? 'bg-primary/10 text-primary'
                                                    : 'hover:bg-muted'
                                            )}
                                        >
                                            <div
                                                className={cn(
                                                    'h-4 w-4 rounded border flex items-center justify-center',
                                                    isSelected
                                                        ? 'bg-primary border-primary'
                                                        : 'border-input'
                                                )}
                                            >
                                                {isSelected && (
                                                    <svg
                                                        className="h-3 w-3 text-primary-foreground"
                                                        fill="none"
                                                        viewBox="0 0 24 24"
                                                        stroke="currentColor"
                                                    >
                                                        <path
                                                            strokeLinecap="round"
                                                            strokeLinejoin="round"
                                                            strokeWidth={2}
                                                            d="M5 13l4 4L19 7"
                                                        />
                                                    </svg>
                                                )}
                                            </div>
                                            <LabelBadge
                                                label={label}
                                                size="sm"
                                                showCategory={false}
                                            />
                                            {label.resource_count !== undefined && (
                                                <span className="ml-auto text-xs text-muted-foreground">
                                                    {label.resource_count}
                                                </span>
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
