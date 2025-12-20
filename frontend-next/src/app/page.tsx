import dynamic from 'next/dynamic';

// Loading component without any shadcn/ui dependencies
function LoadingSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        <p className="text-gray-600">Loading...</p>
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
