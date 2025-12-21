import dynamic from 'next/dynamic';

// Pure CSS loading skeleton - no dependencies
function LoadingSkeleton({ className }: { className?: string }) {
    return (
        <div
            className={`animate-pulse rounded bg-muted ${className || ''}`}
        />
    );
}

// Loading card component
function LoadingCard() {
    return (
        <div className="rounded-2xl border border-border/70 bg-card/90 p-6 shadow-[0_20px_60px_-45px_rgba(15,23,42,0.55)]">
            <LoadingSkeleton className="mb-2 h-8 w-16" />
            <LoadingSkeleton className="h-4 w-24" />
        </div>
    );
}

// Loading component without any shadcn/ui dependencies
function DashboardLoading() {
    return (
        <div className="min-h-screen">
            <header className="border-b border-border/60 bg-background/80 backdrop-blur">
                <div className="container mx-auto flex h-16 items-center justify-between px-4">
                    <LoadingSkeleton className="h-8 w-48" />
                    <LoadingSkeleton className="h-10 w-10 rounded-full" />
                </div>
            </header>
            <main className="container mx-auto p-4 sm:p-6">
                <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <LoadingCard />
                    <LoadingCard />
                    <LoadingCard />
                    <LoadingCard />
                </div>
                <LoadingSkeleton className="h-96 w-full" />
            </main>
        </div>
    );
}

// Dynamically import the client component with SSR disabled
const DashboardClient = dynamic(
    () => import('@/components/pages/dashboard-client'),
    {
        ssr: false,
        loading: () => <DashboardLoading />,
    }
);

export default function DashboardPage() {
    return <DashboardClient />;
}
