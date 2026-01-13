/**
 * Label Selector component for multi-select label assignment.
 */

'use client';

import * as React from 'react';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Check, ChevronsUpDown, Plus, Search } from 'lucide-react';
import { toast } from 'sonner';

import { cn } from '@/lib/utils';
import { labelsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from '@/components/ui/command';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { LabelBadge, type LabelData } from '@/components/LabelBadge';

interface LabelSelectorProps {
    selectedLabels: LabelData[];
    onChange: (labels: LabelData[]) => void;
    isAdmin?: boolean;
    className?: string;
}

export function LabelSelector({
    selectedLabels,
    onChange,
    isAdmin = false,
    className,
}: LabelSelectorProps) {
    const [open, setOpen] = useState(false);
    const [labels, setLabels] = useState<LabelData[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [newLabel, setNewLabel] = useState({
        category: '',
        value: '',
        color: '#6366f1',
    });

    const fetchLabels = useCallback(async () => {
        setLoading(true);
        try {
            const response = await labelsApi.list({ limit: 100 });
            setLabels(response.data.data || []);
        } catch (error) {
            console.error('Failed to fetch labels:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (open) {
            fetchLabels();
        }
    }, [open, fetchLabels]);

    // Group labels by category
    const groupedLabels = useMemo(() => {
        const filtered = labels.filter(
            (label) =>
                label.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
                label.value.toLowerCase().includes(searchQuery.toLowerCase())
        );

        const groups: Record<string, LabelData[]> = {};
        filtered.forEach((label) => {
            if (!groups[label.category]) {
                groups[label.category] = [];
            }
            groups[label.category].push(label);
        });
        return groups;
    }, [labels, searchQuery]);

    const selectedIds = new Set(selectedLabels.map((l) => l.id));

    const toggleLabel = (label: LabelData) => {
        if (selectedIds.has(label.id)) {
            onChange(selectedLabels.filter((l) => l.id !== label.id));
        } else {
            onChange([...selectedLabels, label]);
        }
    };

    const handleCreateLabel = async () => {
        if (!newLabel.category.trim() || !newLabel.value.trim()) {
            toast.error('Category and value are required');
            return;
        }

        try {
            const response = await labelsApi.create({
                category: newLabel.category.trim(),
                value: newLabel.value.trim(),
                color: newLabel.color,
            });
            const createdLabel = response.data;
            setLabels((prev) => [...prev, createdLabel]);
            onChange([...selectedLabels, createdLabel]);
            setCreateDialogOpen(false);
            setNewLabel({ category: '', value: '', color: '#6366f1' });
            toast.success('Label created');
        } catch {
            toast.error('Failed to create label');
        }
    };

    return (
        <div className={cn('space-y-2', className)}>
            {/* Selected labels display */}
            {selectedLabels.length > 0 && (
                <div className="flex flex-wrap gap-1">
                    {selectedLabels.map((label) => (
                        <LabelBadge
                            key={label.id}
                            label={label}
                            size="sm"
                            showCategory={false}
                            onRemove={() => toggleLabel(label)}
                        />
                    ))}
                </div>
            )}

            {/* Selector popover trigger */}
            <Button
                variant="outline"
                size="sm"
                onClick={() => setOpen(true)}
                className="w-full justify-between"
            >
                <span className="flex items-center gap-2">
                    <Search className="h-3 w-3" />
                    Add labels...
                </span>
                <ChevronsUpDown className="h-3 w-3 opacity-50" />
            </Button>

            {/* Selection dialog */}
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>Select Labels</DialogTitle>
                        <DialogDescription>
                            Choose labels to assign to this resource.
                        </DialogDescription>
                    </DialogHeader>

                    <Command className="border rounded-lg">
                        <CommandInput
                            placeholder="Search labels..."
                            value={searchQuery}
                            onValueChange={setSearchQuery}
                        />
                        <CommandList className="max-h-64">
                            {loading ? (
                                <div className="p-4 text-center text-sm text-muted-foreground">
                                    Loading...
                                </div>
                            ) : Object.keys(groupedLabels).length === 0 ? (
                                <CommandEmpty>No labels found.</CommandEmpty>
                            ) : (
                                Object.entries(groupedLabels).map(([category, categoryLabels]) => (
                                    <CommandGroup key={category} heading={category}>
                                        {categoryLabels.map((label) => (
                                            <CommandItem
                                                key={label.id}
                                                value={label.full_name}
                                                onSelect={() => toggleLabel(label)}
                                                className="cursor-pointer"
                                            >
                                                <Check
                                                    className={cn(
                                                        'mr-2 h-4 w-4',
                                                        selectedIds.has(label.id) ? 'opacity-100' : 'opacity-0'
                                                    )}
                                                />
                                                <LabelBadge label={label} size="sm" showCategory={false} />
                                                {label.resource_count !== undefined && (
                                                    <span className="ml-auto text-xs text-muted-foreground">
                                                        {label.resource_count} resources
                                                    </span>
                                                )}
                                            </CommandItem>
                                        ))}
                                    </CommandGroup>
                                ))
                            )}
                        </CommandList>
                    </Command>

                    <DialogFooter className="flex-row gap-2 sm:justify-between">
                        {isAdmin && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setCreateDialogOpen(true)}
                            >
                                <Plus className="mr-1 h-3 w-3" />
                                Create New
                            </Button>
                        )}
                        <Button onClick={() => setOpen(false)}>Done</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Create label dialog */}
            {isAdmin && (
                <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Create New Label</DialogTitle>
                            <DialogDescription>
                                Add a new label that can be assigned to resources.
                            </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-4">
                            <div>
                                <label className="text-sm font-medium">Category</label>
                                <Input
                                    placeholder="e.g., environment, team, type"
                                    value={newLabel.category}
                                    onChange={(e) =>
                                        setNewLabel((prev) => ({ ...prev, category: e.target.value }))
                                    }
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium">Value</label>
                                <Input
                                    placeholder="e.g., production, backend, server"
                                    value={newLabel.value}
                                    onChange={(e) =>
                                        setNewLabel((prev) => ({ ...prev, value: e.target.value }))
                                    }
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium">Color</label>
                                <div className="flex gap-2 items-center">
                                    <input
                                        type="color"
                                        value={newLabel.color}
                                        onChange={(e) =>
                                            setNewLabel((prev) => ({ ...prev, color: e.target.value }))
                                        }
                                        className="h-8 w-12 rounded border cursor-pointer"
                                    />
                                    <Input
                                        value={newLabel.color}
                                        onChange={(e) =>
                                            setNewLabel((prev) => ({ ...prev, color: e.target.value }))
                                        }
                                        placeholder="#6366f1"
                                        className="flex-1"
                                    />
                                </div>
                            </div>
                            {/* Preview */}
                            {newLabel.category && newLabel.value && (
                                <div>
                                    <label className="text-sm font-medium">Preview</label>
                                    <div className="mt-1">
                                        <LabelBadge
                                            label={{
                                                id: 0,
                                                category: newLabel.category,
                                                value: newLabel.value,
                                                color: newLabel.color,
                                                full_name: `${newLabel.category}:${newLabel.value}`,
                                            }}
                                            size="md"
                                        />
                                    </div>
                                </div>
                            )}
                        </div>

                        <DialogFooter>
                            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                                Cancel
                            </Button>
                            <Button onClick={handleCreateLabel}>Create</Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            )}
        </div>
    );
}
