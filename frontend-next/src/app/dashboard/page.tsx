import dynamic from 'next/dynamic';

// Pure CSS loading skeleton - no dependencies
function LoadingSkeleton({ className }: { className?: string }) {
    return (
        <div
            className={`animate-pulse rounded bg-gray-200 ${className || ''}`}
        />
    );
}

// Loading card component
function LoadingCard() {
    return (
        <div className="rounded-lg border bg-white p-6 shadow-sm">
            <LoadingSkeleton className="mb-2 h-8 w-16" />
            <LoadingSkeleton className="h-4 w-24" />
        </div>
    );
}

// Loading component without any shadcn/ui dependencies
function DashboardLoading() {
    return (
        <div className="min-h-screen bg-gray-50">
            <header className="border-b bg-white">
                <div className="container mx-auto flex h-16 items-center justify-between px-4">
                    <LoadingSkeleton className="h-8 w-48" />
                    <LoadingSkeleton className="h-10 w-10 rounded-full" />
                </div>
            </header>
            <main className="container mx-auto p-4">
                <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
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
