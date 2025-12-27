/**
 * Admin roles page.
 */

import dynamic from 'next/dynamic';

function LoadingSkeleton({ className }: { className?: string }) {
    return <div className={`animate-pulse rounded bg-muted ${className || ''}`} />;
}

function AdminRolesLoading() {
    return (
        <div className="min-h-screen">
            <header className="border-b border-border/60 bg-background/80 backdrop-blur">
                <div className="container mx-auto flex h-16 items-center justify-between px-4">
                    <LoadingSkeleton className="h-8 w-48" />
                    <LoadingSkeleton className="h-9 w-28" />
                </div>
            </header>
            <main className="container mx-auto space-y-6 p-4 sm:p-6">
                <LoadingSkeleton className="h-36 w-full" />
                <div className="grid gap-6 lg:grid-cols-3">
                    <LoadingSkeleton className="h-64 w-full" />
                    <LoadingSkeleton className="h-64 w-full" />
                    <LoadingSkeleton className="h-64 w-full" />
                </div>
            </main>
        </div>
    );
}

const AdminRolesClient = dynamic(() => import('@/components/pages/admin-roles-client'), {
    ssr: false,
    loading: () => <AdminRolesLoading />,
});

export default function AdminRolesPage() {
    return <AdminRolesClient />;
}
