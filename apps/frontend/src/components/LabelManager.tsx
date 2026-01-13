/**
 * Label Manager component for admin CRUD operations on labels.
 */

'use client';

import * as React from 'react';
import { useState, useEffect, useCallback } from 'react';
import {
    Plus,
    Pencil,
    Trash2,
    GitMerge,
    Search,
    Loader2,
} from 'lucide-react';
import { toast } from 'sonner';

import { cn } from '@/lib/utils';
import { labelsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { LabelBadge, type LabelData } from '@/components/LabelBadge';

interface LabelFormData {
    category: string;
    value: string;
    color: string;
    description: string;
}

const DEFAULT_COLORS = [
    '#ef4444', // red
    '#f97316', // orange
    '#eab308', // yellow
    '#22c55e', // green
    '#14b8a6', // teal
    '#3b82f6', // blue
    '#6366f1', // indigo
    '#8b5cf6', // violet
    '#ec4899', // pink
    '#6b7280', // gray
];

export function LabelManager() {
    const [labels, setLabels] = useState<LabelData[]>([]);
    const [categories, setCategories] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [categoryFilter, setCategoryFilter] = useState<string>('all');

    // Dialog states
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [mergeDialogOpen, setMergeDialogOpen] = useState(false);
    const [selectedLabel, setSelectedLabel] = useState<LabelData | null>(null);
    const [formData, setFormData] = useState<LabelFormData>({
        category: '',
        value: '',
        color: '#6366f1',
        description: '',
    });

    // Merge state
    const [mergeSource, setMergeSource] = useState<number[]>([]);
    const [mergeTarget, setMergeTarget] = useState<number | null>(null);

    const fetchLabels = useCallback(async () => {
        setLoading(true);
        try {
            const [labelsRes, categoriesRes] = await Promise.all([
                labelsApi.list({ limit: 100 }),
                labelsApi.getCategories(),
            ]);
            setLabels(labelsRes.data.data || []);
            setCategories(categoriesRes.data.map((c: { category: string }) => c.category));
        } catch {
            toast.error('Failed to load labels');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchLabels();
    }, [fetchLabels]);

    const filteredLabels = labels.filter((label) => {
        const matchesSearch =
            label.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
            label.value.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesCategory =
            categoryFilter === 'all' || label.category === categoryFilter;
        return matchesSearch && matchesCategory;
    });

    const openCreateDialog = () => {
        setSelectedLabel(null);
        setFormData({
            category: '',
            value: '',
            color: '#6366f1',
            description: '',
        });
        setEditDialogOpen(true);
    };

    const openEditDialog = (label: LabelData) => {
        setSelectedLabel(label);
        setFormData({
            category: label.category,
            value: label.value,
            color: label.color,
            description: label.description || '',
        });
        setEditDialogOpen(true);
    };

    const openDeleteDialog = (label: LabelData) => {
        setSelectedLabel(label);
        setDeleteDialogOpen(true);
    };

    const handleSave = async () => {
        if (!formData.category.trim() || !formData.value.trim()) {
            toast.error('Category and value are required');
            return;
        }

        try {
            if (selectedLabel) {
                await labelsApi.update(selectedLabel.id, {
                    category: formData.category.trim(),
                    value: formData.value.trim(),
                    color: formData.color,
                    description: formData.description.trim() || undefined,
                });
                toast.success('Label updated');
            } else {
                await labelsApi.create({
                    category: formData.category.trim(),
                    value: formData.value.trim(),
                    color: formData.color,
                    description: formData.description.trim() || undefined,
                });
                toast.success('Label created');
            }
            setEditDialogOpen(false);
            fetchLabels();
        } catch {
            toast.error(selectedLabel ? 'Failed to update label' : 'Failed to create label');
        }
    };

    const handleDelete = async () => {
        if (!selectedLabel) return;

        try {
            await labelsApi.delete(selectedLabel.id);
            toast.success('Label deleted');
            setDeleteDialogOpen(false);
            fetchLabels();
        } catch {
            toast.error('Failed to delete label');
        }
    };

    const handleMerge = async () => {
        if (mergeSource.length === 0 || !mergeTarget) {
            toast.error('Select source and target labels');
            return;
        }

        try {
            await labelsApi.merge({
                source_label_ids: mergeSource,
                target_label_id: mergeTarget,
            });
            toast.success('Labels merged successfully');
            setMergeDialogOpen(false);
            setMergeSource([]);
            setMergeTarget(null);
            fetchLabels();
        } catch {
            toast.error('Failed to merge labels');
        }
    };

    const toggleMergeSource = (labelId: number) => {
        if (mergeSource.includes(labelId)) {
            setMergeSource(mergeSource.filter((id) => id !== labelId));
        } else {
            setMergeSource([...mergeSource, labelId]);
            // Clear target if it was selected as source
            if (mergeTarget === labelId) {
                setMergeTarget(null);
            }
        }
    };

    // Group labels by category for display
    const groupedLabels: Record<string, LabelData[]> = {};
    filteredLabels.forEach((label) => {
        if (!groupedLabels[label.category]) {
            groupedLabels[label.category] = [];
        }
        groupedLabels[label.category].push(label);
    });

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle>Label Management</CardTitle>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setMergeDialogOpen(true)}
                    >
                        <GitMerge className="mr-2 h-4 w-4" />
                        Merge
                    </Button>
                    <Button size="sm" onClick={openCreateDialog}>
                        <Plus className="mr-2 h-4 w-4" />
                        New Label
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                {/* Filters */}
                <div className="mb-4 flex gap-2">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            placeholder="Search labels..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-9"
                        />
                    </div>
                    <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="All Categories" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Categories</SelectItem>
                            {categories.map((cat) => (
                                <SelectItem key={cat} value={cat}>
                                    {cat}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                {/* Labels list */}
                {loading ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                ) : filteredLabels.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                        No labels found. Create one to get started.
                    </div>
                ) : (
                    <div className="space-y-4">
                        {Object.entries(groupedLabels).map(([category, categoryLabels]) => (
                            <div key={category}>
                                <h3 className="text-sm font-medium text-muted-foreground mb-2">
                                    {category}
                                </h3>
                                <div className="space-y-1">
                                    {categoryLabels.map((label) => (
                                        <div
                                            key={label.id}
                                            className="flex items-center justify-between p-2 rounded-lg border hover:bg-muted/50 transition-colors"
                                        >
                                            <div className="flex items-center gap-3">
                                                <LabelBadge label={label} size="md" showCategory={false} />
                                                {label.description && (
                                                    <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                                                        {label.description}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-muted-foreground">
                                                    {label.resource_count ?? 0} resources
                                                </span>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => openEditDialog(label)}
                                                >
                                                    <Pencil className="h-3 w-3" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => openDeleteDialog(label)}
                                                >
                                                    <Trash2 className="h-3 w-3" />
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>

            {/* Edit/Create Dialog */}
            <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            {selectedLabel ? 'Edit Label' : 'Create Label'}
                        </DialogTitle>
                        <DialogDescription>
                            {selectedLabel
                                ? 'Update the label details below.'
                                : 'Create a new label for categorizing resources.'}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                        <div>
                            <label className="text-sm font-medium">Category *</label>
                            <Input
                                placeholder="e.g., environment, team, type"
                                value={formData.category}
                                onChange={(e) =>
                                    setFormData((prev) => ({ ...prev, category: e.target.value }))
                                }
                                list="category-suggestions"
                            />
                            <datalist id="category-suggestions">
                                {categories.map((cat) => (
                                    <option key={cat} value={cat} />
                                ))}
                            </datalist>
                        </div>
                        <div>
                            <label className="text-sm font-medium">Value *</label>
                            <Input
                                placeholder="e.g., production, backend, server"
                                value={formData.value}
                                onChange={(e) =>
                                    setFormData((prev) => ({ ...prev, value: e.target.value }))
                                }
                            />
                        </div>
                        <div>
                            <label className="text-sm font-medium">Color</label>
                            <div className="flex gap-2 items-center mt-1">
                                <input
                                    type="color"
                                    value={formData.color}
                                    onChange={(e) =>
                                        setFormData((prev) => ({ ...prev, color: e.target.value }))
                                    }
                                    className="h-8 w-10 rounded border cursor-pointer"
                                />
                                <div className="flex gap-1">
                                    {DEFAULT_COLORS.map((color) => (
                                        <button
                                            key={color}
                                            type="button"
                                            onClick={() => setFormData((prev) => ({ ...prev, color }))}
                                            className={cn(
                                                'h-6 w-6 rounded-full border-2 transition-transform hover:scale-110',
                                                formData.color === color
                                                    ? 'border-primary'
                                                    : 'border-transparent'
                                            )}
                                            style={{ backgroundColor: color }}
                                        />
                                    ))}
                                </div>
                            </div>
                        </div>
                        <div>
                            <label className="text-sm font-medium">Description</label>
                            <Input
                                placeholder="Optional description..."
                                value={formData.description}
                                onChange={(e) =>
                                    setFormData((prev) => ({ ...prev, description: e.target.value }))
                                }
                            />
                        </div>
                        {/* Preview */}
                        {formData.category && formData.value && (
                            <div>
                                <label className="text-sm font-medium">Preview</label>
                                <div className="mt-1">
                                    <LabelBadge
                                        label={{
                                            id: selectedLabel?.id ?? 0,
                                            category: formData.category,
                                            value: formData.value,
                                            color: formData.color,
                                            full_name: `${formData.category}:${formData.value}`,
                                            description: formData.description || null,
                                        }}
                                        size="lg"
                                    />
                                </div>
                            </div>
                        )}
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleSave}>
                            {selectedLabel ? 'Save Changes' : 'Create Label'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation */}
            <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Label</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete the label{' '}
                            <strong>{selectedLabel?.full_name}</strong>? This will remove it from{' '}
                            {selectedLabel?.resource_count ?? 0} resources.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Merge Dialog */}
            <Dialog open={mergeDialogOpen} onOpenChange={setMergeDialogOpen}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Merge Labels</DialogTitle>
                        <DialogDescription>
                            Select source labels to merge into a target label. Source labels
                            will be deleted and their resources reassigned.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                        <div>
                            <label className="text-sm font-medium mb-2 block">
                                Source Labels (to be merged)
                            </label>
                            <div className="border rounded-lg p-2 max-h-32 overflow-y-auto space-y-1">
                                {labels.map((label) => (
                                    <button
                                        key={label.id}
                                        type="button"
                                        onClick={() => toggleMergeSource(label.id)}
                                        disabled={mergeTarget === label.id}
                                        className={cn(
                                            'w-full flex items-center gap-2 px-2 py-1 rounded text-left text-sm',
                                            mergeSource.includes(label.id)
                                                ? 'bg-primary/10'
                                                : 'hover:bg-muted',
                                            mergeTarget === label.id && 'opacity-50 cursor-not-allowed'
                                        )}
                                    >
                                        <div
                                            className={cn(
                                                'h-4 w-4 rounded border flex items-center justify-center',
                                                mergeSource.includes(label.id)
                                                    ? 'bg-primary border-primary'
                                                    : 'border-input'
                                            )}
                                        >
                                            {mergeSource.includes(label.id) && (
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
                                        <LabelBadge label={label} size="sm" showCategory />
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <label className="text-sm font-medium mb-2 block">
                                Target Label (keep)
                            </label>
                            <Select
                                value={mergeTarget?.toString() || ''}
                                onValueChange={(val) => setMergeTarget(parseInt(val, 10))}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select target label" />
                                </SelectTrigger>
                                <SelectContent>
                                    {labels
                                        .filter((l) => !mergeSource.includes(l.id))
                                        .map((label) => (
                                            <SelectItem key={label.id} value={label.id.toString()}>
                                                {label.full_name}
                                            </SelectItem>
                                        ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {mergeSource.length > 0 && mergeTarget && (
                            <div className="p-3 bg-muted rounded-lg text-sm">
                                <strong>{mergeSource.length}</strong> label(s) will be merged
                                into{' '}
                                <LabelBadge
                                    label={labels.find((l) => l.id === mergeTarget)!}
                                    size="sm"
                                    showCategory
                                />
                            </div>
                        )}
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setMergeDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleMerge}
                            disabled={mergeSource.length === 0 || !mergeTarget}
                        >
                            Merge Labels
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
