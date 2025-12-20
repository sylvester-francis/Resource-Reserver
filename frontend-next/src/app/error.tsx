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
        <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
            <div className="text-center">
                <h1 className="text-4xl font-bold text-red-600">Something went wrong</h1>
                <p className="mt-4 text-gray-600">
                    {error.message || 'An unexpected error occurred'}
                </p>
                <div className="mt-6 flex gap-4 justify-center">
                    <button
                        onClick={() => reset()}
                        className="rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700 transition-colors"
                    >
                        Try Again
                    </button>
                    <Link
                        href="/"
                        className="rounded-lg border border-gray-300 px-6 py-3 text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                        Go Home
                    </Link>
                </div>
            </div>
        </div>
    );
}
