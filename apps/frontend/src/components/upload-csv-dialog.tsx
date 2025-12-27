/**
 * Upload csv dialog component.
 */

'use client';

import { useState, useRef } from 'react';
import { Upload } from 'lucide-react';
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
import { Alert, AlertDescription } from '@/components/ui/alert';

interface UploadCsvDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: () => void;
}

export function UploadCsvDialog({
    open,
    onOpenChange,
    onSuccess,
}: UploadCsvDialogProps) {
    const [file, setFile] = useState<File | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            if (selectedFile.type !== 'text/csv' && !selectedFile.name.endsWith('.csv')) {
                setError('Please select a CSV file');
                return;
            }
            setFile(selectedFile);
            setError(null);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) return;

        setError(null);
        setIsLoading(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await api.post('/resources/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            const data = response.data;
            toast.success(`Uploaded: ${data.created || 0} created, ${data.updated || 0} updated`);
            onSuccess();
            onOpenChange(false);
            setFile(null);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Upload failed';
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
                    <DialogTitle>Upload Resources CSV</DialogTitle>
                    <DialogDescription>
                        Upload a CSV file to add multiple resources at once.
                    </DialogDescription>
                </DialogHeader>

                <Alert>
                    <AlertDescription>
                        <strong>CSV Format:</strong> name,tags,available
                        <br />
                        <span className="text-muted-foreground text-xs">
                            Example: &quot;Conference Room A&quot;,&quot;meeting,large&quot;,true
                        </span>
                    </AlertDescription>
                </Alert>

                <form onSubmit={handleSubmit}>
                    <div className="grid gap-4 py-4">
                        <div
                            className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 cursor-pointer hover:border-primary/50 transition-colors"
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
                            <p className="text-sm font-medium">
                                {file ? file.name : 'Click to select CSV file'}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {file ? `${(file.size / 1024).toFixed(1)} KB` : 'or drag and drop'}
                            </p>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".csv"
                                onChange={handleFileChange}
                                className="hidden"
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
                        <Button type="submit" disabled={isLoading || !file}>
                            {isLoading ? 'Uploading...' : 'Upload'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
