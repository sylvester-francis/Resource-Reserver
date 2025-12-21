'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import api from '@/lib/api';

export default function HomeClient() {
    const router = useRouter();
    const { isAuthenticated, loading } = useAuth();
    const [setupComplete, setSetupComplete] = useState<boolean | null>(null);

    useEffect(() => {
        let active = true;
        const checkSetup = async () => {
            try {
                const response = await api.get('/setup/status');
                if (!active) return;
                setSetupComplete(!!response.data?.setup_complete);
            } catch {
                if (active) setSetupComplete(true);
            }
        };
        checkSetup();
        return () => {
            active = false;
        };
    }, []);

    useEffect(() => {
        if (setupComplete === false) {
            router.replace('/setup');
            return;
        }
        if (!loading && setupComplete) {
            if (isAuthenticated) {
                router.replace('/dashboard');
            } else {
                router.replace('/login');
            }
        }
    }, [isAuthenticated, loading, router, setupComplete]);

    return (
        <div className="flex min-h-screen items-center justify-center">
            <div className="flex flex-col items-center gap-4 text-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                <p className="text-muted-foreground">Checking authentication...</p>
            </div>
        </div>
    );
}
