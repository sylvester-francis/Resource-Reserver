/**
 * Edit resource dialog component.
 * Allows admins to edit resource name, description, and tags.
 */

'use client';

import { useEffect, useState } from 'react';
import { Pencil } from 'lucide-react';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface Resource {
    id: number;
    name: string;
    description?: string | null;
    tags: string[];
    status: string;
}

interface EditResourceDialogProps {
    resource: Resource;
    onSuccess: () => void;
    disabled?: boolean;
}

export function EditResourceDialog({
    resource,
    onSuccess,
    disabled = false,
}: EditResourceDialogProps) {
    const [open, setOpen] = useState(false);
    const [name, setName] = useState(resource.name);
    const [description, setDescription] = useState(resource.description || '');
    const [tags, setTags] = useState(resource.tags.join(', '));
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Reset form when dialog opens or resource changes
    useEffect(() => {
        if (open) {
            setName(resource.name);
            setDescription(resource.description || '');
            setTags(resource.tags.join(', '));
            setError(null);
        }
    }, [open, resource]);

    const isInUse = resource.status === 'in_use';

    // Don't render anything if user is not admin
    if (disabled) {
        return null;
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            const tagArray = tags
                .split(',')
                .map(t => t.trim())
                .filter(t => t.length > 0);

            await api.put(`/resources/${resource.id}`, {
                name,
                description: description || null,
                tags: tagArray,
            });

            toast.success('Resource updated successfully');
            onSuccess();
            setOpen(false);
        } catch (err: unknown) {
            const errorResponse = err as { response?: { data?: { detail?: string } } };
            const message = errorResponse?.response?.data?.detail || 'Failed to update resource';
            setError(message);
            toast.error(message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button
                    variant="outline"
                    size="sm"
                    disabled={disabled || isInUse}
                    title={isInUse ? 'Cannot edit a resource that is in use' : 'Edit resource'}
                >
                    <Pencil className="h-4 w-4" />
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Edit Resource</DialogTitle>
                    <DialogDescription>
                        Update the resource details. The resource must not be in use.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit}>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="edit-name">Resource Name</Label>
                            <Input
                                id="edit-name"
                                placeholder="e.g., Conference Room A"
                                value={name}
                                onChange={e => setName(e.target.value)}
                                required
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="edit-description">Description</Label>
                            <Textarea
                                id="edit-description"
                                placeholder="e.g., Large conference room with projector and whiteboard"
                                value={description}
                                onChange={e => setDescription(e.target.value)}
                                rows={3}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="edit-tags">Tags (comma-separated)</Label>
                            <Input
                                id="edit-tags"
                                placeholder="e.g., meeting, conference, projector"
                                value={tags}
                                onChange={e => setTags(e.target.value)}
                            />
                        </div>
                        {error && (
                            <p className="text-sm text-destructive">{error}</p>
                        )}
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isLoading}>
                            {isLoading ? 'Saving...' : 'Save Changes'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
