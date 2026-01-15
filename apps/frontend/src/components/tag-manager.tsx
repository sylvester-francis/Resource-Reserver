/**
 * Tag Manager component for admin CRUD operations on tags.
 * Allows admins to view, rename, and delete tags globally.
 */

'use client';

import { useEffect, useState } from 'react';
import { Settings, Pencil, Trash2, Tag, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

import api from '@/lib/api';

import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
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
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

interface TagInfo {
    name: string;
    resource_count: number;
}

interface TagManagerProps {
    onTagsChanged?: () => void;
}

export function TagManager({ onTagsChanged }: TagManagerProps) {
    const [open, setOpen] = useState(false);
    const [tags, setTags] = useState<TagInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const [editingTag, setEditingTag] = useState<string | null>(null);
    const [newTagName, setNewTagName] = useState('');
    const [deletingTag, setDeletingTag] = useState<string | null>(null);
    const [actionLoading, setActionLoading] = useState(false);

    const fetchTags = async () => {
        setLoading(true);
        try {
            const response = await api.get('/resources/tags/details');
            setTags(response.data);
        } catch (err: unknown) {
            const errorResponse = err as { response?: { data?: { detail?: string }; status?: number } };
            if (errorResponse?.response?.status === 403) {
                toast.error('Admin access required to manage tags');
            } else {
                toast.error('Failed to load tags');
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (open) {
            fetchTags();
        }
    }, [open]);

    const handleStartRename = (tagName: string) => {
        setEditingTag(tagName);
        setNewTagName(tagName);
    };

    const handleCancelRename = () => {
        setEditingTag(null);
        setNewTagName('');
    };

    // Check if the new tag name conflicts with an existing tag (case-insensitive)
    const isDuplicateTagName = (): boolean => {
        if (!newTagName.trim() || !editingTag) return false;
        const trimmedNewName = newTagName.trim().toLowerCase();
        // Allow same name (no actual change)
        if (trimmedNewName === editingTag.toLowerCase()) return false;
        // Check if any other tag has this name
        return tags.some(tag => tag.name.toLowerCase() === trimmedNewName);
    };

    const handleRename = async () => {
        if (!editingTag || !newTagName.trim()) return;
        if (newTagName.trim() === editingTag) {
            handleCancelRename();
            return;
        }

        setActionLoading(true);
        try {
            await api.put('/resources/tags/rename', {
                old_name: editingTag,
                new_name: newTagName.trim(),
            });
            toast.success(`Tag renamed from "${editingTag}" to "${newTagName.trim()}"`);
            handleCancelRename();
            await fetchTags();
            onTagsChanged?.();
        } catch (err: unknown) {
            const errorResponse = err as { response?: { data?: { detail?: string } } };
            const message = errorResponse?.response?.data?.detail || 'Failed to rename tag';
            toast.error(message);
        } finally {
            setActionLoading(false);
        }
    };

    const handleDelete = async () => {
        if (!deletingTag) return;

        setActionLoading(true);
        try {
            await api.delete(`/resources/tags/${encodeURIComponent(deletingTag)}`);
            toast.success(`Tag "${deletingTag}" deleted from all resources`);
            setDeletingTag(null);
            await fetchTags();
            onTagsChanged?.();
        } catch (err: unknown) {
            const errorResponse = err as { response?: { data?: { detail?: string } } };
            const message = errorResponse?.response?.data?.detail || 'Failed to delete tag';
            toast.error(message);
        } finally {
            setActionLoading(false);
        }
    };

    return (
        <>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogTrigger asChild>
                    <Button variant="outline" size="sm">
                        <Settings className="mr-2 h-4 w-4" />
                        Manage Tags
                    </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[500px]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Tag className="h-5 w-5" />
                            Tag Management
                        </DialogTitle>
                        <DialogDescription>
                            Rename or delete tags globally. Changes will affect all resources with these tags.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="h-[400px] overflow-y-auto pr-4">
                        {loading ? (
                            <div className="space-y-2">
                                {[1, 2, 3, 4, 5].map(i => (
                                    <div key={i} className="h-12 bg-muted animate-pulse rounded-md" />
                                ))}
                            </div>
                        ) : tags.length === 0 ? (
                            <div className="text-center py-8 text-muted-foreground">
                                No tags found. Tags are created when you add them to resources.
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {tags.map(tag => (
                                    <div
                                        key={tag.name}
                                        className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50"
                                    >
                                        {editingTag === tag.name ? (
                                            <div className="flex-1 flex flex-col gap-2">
                                                <div className="flex items-center gap-2">
                                                    <Input
                                                        value={newTagName}
                                                        onChange={e => setNewTagName(e.target.value)}
                                                        className={`h-8 ${isDuplicateTagName() ? 'border-destructive' : ''}`}
                                                        autoFocus
                                                        onKeyDown={e => {
                                                            if (e.key === 'Enter' && !isDuplicateTagName()) handleRename();
                                                            if (e.key === 'Escape') handleCancelRename();
                                                        }}
                                                    />
                                                    <Button
                                                        size="sm"
                                                        onClick={handleRename}
                                                        disabled={actionLoading || !newTagName.trim() || isDuplicateTagName()}
                                                    >
                                                        Save
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={handleCancelRename}
                                                        disabled={actionLoading}
                                                    >
                                                        Cancel
                                                    </Button>
                                                </div>
                                                {isDuplicateTagName() && (
                                                    <div className="flex items-center gap-1.5 text-sm text-destructive">
                                                        <AlertTriangle className="h-4 w-4" />
                                                        <span>A tag with this name already exists. Tag names must be unique.</span>
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <>
                                                <div className="flex items-center gap-2">
                                                    <Badge variant="outline">{tag.name}</Badge>
                                                    <span className="text-sm text-muted-foreground">
                                                        {tag.resource_count} resource{tag.resource_count !== 1 ? 's' : ''}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-1">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => handleStartRename(tag.name)}
                                                        title="Rename tag"
                                                    >
                                                        <Pencil className="h-4 w-4" />
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => setDeletingTag(tag.name)}
                                                        className="text-destructive hover:text-destructive"
                                                        title="Delete tag"
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)}>
                            Close
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <AlertDialog open={!!deletingTag} onOpenChange={() => setDeletingTag(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Tag</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete the tag &quot;{deletingTag}&quot;? 
                            This will remove it from all resources that currently have this tag.
                            This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={actionLoading}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDelete}
                            disabled={actionLoading}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {actionLoading ? 'Deleting...' : 'Delete Tag'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}
