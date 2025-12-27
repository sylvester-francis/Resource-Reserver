/**
 * Home page.
 */

import dynamic from 'next/dynamic';

// Loading component without any shadcn/ui dependencies
function LoadingSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}

// Dynamically import the client component with SSR disabled
const HomeClient = dynamic(() => import('@/components/pages/home-client'), {
  ssr: false,
  loading: () => <LoadingSpinner />,
});

export default function Home() {
  return <HomeClient />;
}
