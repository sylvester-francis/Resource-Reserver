import dynamic from 'next/dynamic';

// Pure CSS loading skeleton - no dependencies
function LoadingSkeleton({ className }: { className?: string }) {
    return (
        <div
            className={`animate-pulse rounded bg-gray-200 ${className || ''}`}
        />
    );
}

// Loading component without any shadcn/ui dependencies
function LoginLoading() {
    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
            <div className="w-full max-w-md rounded-lg border bg-white p-6 shadow-sm">
                <div className="space-y-4 text-center">
                    <LoadingSkeleton className="mx-auto h-12 w-12 rounded-full" />
                    <LoadingSkeleton className="mx-auto h-6 w-32" />
                    <LoadingSkeleton className="mx-auto h-4 w-48" />
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

// Dynamically import the client component with SSR disabled
const LoginClient = dynamic(() => import('@/components/pages/login-client'), {
    ssr: false,
    loading: () => <LoginLoading />,
});

export default function LoginPage() {
    return <LoginClient />;
}
