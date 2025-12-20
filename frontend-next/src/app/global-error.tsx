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
                <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
                    <div className="text-center">
                        <h1 className="text-6xl font-bold text-red-600">Error</h1>
                        <p className="mt-4 text-xl text-gray-600">Something went wrong!</p>
                        <p className="mt-2 text-gray-500">
                            An unexpected error occurred. Please try again.
                        </p>
                        <button
                            onClick={() => reset()}
                            className="mt-6 inline-block rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700 transition-colors"
                        >
                            Try Again
                        </button>
                    </div>
                </div>
            </body>
        </html>
    );
}
