import Link from 'next/link';

export default function NotFound() {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center">
            <div className="text-center">
                <h1 className="font-display text-6xl text-foreground">404</h1>
                <p className="mt-4 text-xl text-foreground">Page not found</p>
                <p className="mt-2 text-muted-foreground">
                    The page you&apos;re looking for doesn&apos;t exist or has been moved.
                </p>
                <Link
                    href="/"
                    className="mt-6 inline-flex items-center justify-center rounded-lg bg-primary px-6 py-3 text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
                >
                    Go Home
                </Link>
            </div>
        </div>
    );
}
