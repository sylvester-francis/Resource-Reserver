/**
 * Setup page.
 */

import dynamic from 'next/dynamic';

function LoadingSkeleton({ className }: { className?: string }) {
    return <div className={`animate-pulse rounded bg-muted ${className || ''}`} />;
}

function SetupLoading() {
    return (
        <div className="flex min-h-screen items-center justify-center px-4">
            <div className="w-full max-w-md rounded-2xl border border-border/70 bg-card/90 p-6 shadow-[0_20px_60px_-45px_rgba(15,23,42,0.55)]">
                <div className="space-y-4 text-center">
                    <LoadingSkeleton className="mx-auto h-12 w-12 rounded-2xl" />
                    <LoadingSkeleton className="mx-auto h-6 w-40" />
                    <LoadingSkeleton className="mx-auto h-4 w-56" />
                </div>
                <div className="mt-6 space-y-4">
                    <LoadingSkeleton className="h-10 w-full" />
                    <LoadingSkeleton className="h-10 w-full" />
                    <LoadingSkeleton className="h-10 w-full" />
                </div>
            </div>
        </div>
    );
}

const SetupClient = dynamic(() => import('@/components/pages/setup-client'), {
    ssr: false,
    loading: () => <SetupLoading />,
});

export default function SetupPage() {
    return <SetupClient />;
}
