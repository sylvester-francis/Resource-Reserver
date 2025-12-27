/**
 * Error.
 */

'use client';

import { useEffect } from 'react';
import Link from 'next/link';

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('Page error:', error);
    }, [error]);

    return (
        <div className="flex min-h-screen flex-col items-center justify-center">
            <div className="text-center">
                <h1 className="font-display text-4xl text-destructive">Something went wrong</h1>
                <p className="mt-4 text-muted-foreground">
                    {error.message || 'An unexpected error occurred'}
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-4">
                    <button
                        onClick={() => reset()}
                        className="rounded-lg bg-primary px-6 py-3 text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
                    >
                        Try Again
                    </button>
                    <Link
                        href="/"
                        className="rounded-lg border border-border px-6 py-3 text-foreground transition-colors hover:bg-muted/60"
                    >
                        Go Home
                    </Link>
                </div>
            </div>
        </div>
    );
}
