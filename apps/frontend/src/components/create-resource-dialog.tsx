/**
 * Create resource dialog component.
 */

'use client';

import { useState } from 'react';
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
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';

interface CreateResourceDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: () => void;
}

export function CreateResourceDialog({
    open,
    onOpenChange,
    onSuccess,
}: CreateResourceDialogProps) {
    const [name, setName] = useState('');
    const [tags, setTags] = useState('');
    const [available, setAvailable] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            const tagArray = tags
                .split(',')
                .map(t => t.trim())
                .filter(t => t.length > 0);

            await api.post('/resources', {
                name,
                tags: tagArray,
                available,
            });

            toast.success('Resource created successfully');
            onSuccess();
            onOpenChange(false);

            // Reset form
            setName('');
            setTags('');
            setAvailable(true);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to create resource';
            setError(message);
            toast.error(message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Create Resource</DialogTitle>
                    <DialogDescription>
                        Add a new resource to the reservation system.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit}>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="name">Resource Name</Label>
                            <Input
                                id="name"
                                placeholder="e.g., Conference Room A"
                                value={name}
                                onChange={e => setName(e.target.value)}
                                required
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="tags">Tags (comma-separated)</Label>
                            <Input
                                id="tags"
                                placeholder="e.g., meeting, conference, projector"
                                value={tags}
                                onChange={e => setTags(e.target.value)}
                            />
                        </div>
                        <div className="flex items-center justify-between">
                            <Label htmlFor="available">Available for booking</Label>
                            <Switch
                                id="available"
                                checked={available}
                                onCheckedChange={setAvailable}
                            />
                        </div>
                        {error && (
                            <p className="text-sm text-destructive">{error}</p>
                        )}
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isLoading}>
                            {isLoading ? 'Creating...' : 'Create Resource'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
