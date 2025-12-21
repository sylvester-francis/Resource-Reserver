'use client';

import { useEffect } from 'react';

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        // Log the error to an error reporting service
        console.error('Global error:', error);
    }, [error]);

    return (
        <html>
            <body>
                <div className="flex min-h-screen flex-col items-center justify-center">
                    <div className="text-center">
                        <h1 className="font-display text-6xl text-destructive">Error</h1>
                        <p className="mt-4 text-xl text-foreground">Something went wrong!</p>
                        <p className="mt-2 text-muted-foreground">
                            An unexpected error occurred. Please try again.
                        </p>
                        <button
                            onClick={() => reset()}
                            className="mt-6 inline-flex items-center justify-center rounded-lg bg-primary px-6 py-3 text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
                        >
                            Try Again
                        </button>
                    </div>
                </div>
            </body>
        </html>
    );
}
