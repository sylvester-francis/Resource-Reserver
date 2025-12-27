/**
 * Setup client component.
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, UserPlus, KeyRound } from 'lucide-react';
import { toast } from 'sonner';

import api from '@/lib/api';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ThemeToggle } from '@/components/theme-toggle';
import { Skeleton } from '@/components/ui/skeleton';

type SetupStatus = {
    setup_complete: boolean;
    setup_reopened: boolean;
};

export default function SetupClient() {
    const router = useRouter();
    const [status, setStatus] = useState<SetupStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [mode, setMode] = useState<'create' | 'promote'>('create');
    const [token, setToken] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [existingUsername, setExistingUsername] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        let active = true;
        const fetchStatus = async () => {
            try {
                const response = await api.get('/setup/status');
                if (!active) return;
                setStatus(response.data);
                if (response.data?.setup_complete) {
                    router.replace('/login');
                }
            } catch (err) {
                if (!active) return;
                setError(err instanceof Error ? err.message : 'Failed to load setup status');
            } finally {
                if (active) setLoading(false);
            }
        };
        fetchStatus();
        return () => {
            active = false;
        };
    }, [router]);

    const submitSetup = async (event: React.FormEvent) => {
        event.preventDefault();
        setError(null);
        setSuccess(null);

        if (status?.setup_reopened && !token.trim()) {
            setError('Setup unlock token is required.');
            return;
        }

        if (mode === 'create') {
            if (!username.trim() || !password) {
                setError('Username and password are required.');
                return;
            }
            if (password !== confirmPassword) {
                setError('Passwords do not match.');
                return;
            }
        } else if (!existingUsername.trim()) {
            setError('Existing username is required.');
            return;
        }

        setIsSubmitting(true);
        try {
            const payload =
                mode === 'create'
                    ? { username: username.trim(), password }
                    : { existing_username: existingUsername.trim() };
            await api.post('/setup/initialize', payload, {
                headers: token.trim() ? { 'X-Setup-Token': token.trim() } : undefined,
            });
            setSuccess('Setup completed. You can now sign in as an administrator.');
            toast.success('Setup completed successfully');
            setUsername('');
            setPassword('');
            setConfirmPassword('');
            setExistingUsername('');
            setTimeout(() => router.replace('/login'), 1200);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Setup failed';
            setError(message);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex min-h-screen items-center justify-center px-4">
                <Card className="w-full max-w-md">
                    <CardHeader className="space-y-2 text-center">
                        <Skeleton className="h-12 w-12 rounded-2xl mx-auto" />
                        <Skeleton className="h-6 w-40 mx-auto" />
                        <Skeleton className="h-4 w-56 mx-auto" />
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-10 w-full" />
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (status?.setup_complete) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="flex flex-col items-center gap-4 text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                    <p className="text-muted-foreground">Setup already complete. Redirecting...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="relative min-h-screen overflow-hidden">
            <div className="pointer-events-none absolute -top-40 right-[-10%] h-[420px] w-[420px] rounded-full bg-primary/15 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-40 left-[-10%] h-[360px] w-[360px] rounded-full bg-secondary/50 blur-3xl" />
            <div className="absolute right-6 top-6 z-10">
                <ThemeToggle />
            </div>

            <div className="container mx-auto grid min-h-screen items-center gap-10 px-4 py-12 lg:grid-cols-[1.1fr_0.9fr]">
                <div className="hidden flex-col gap-6 lg:flex">
                    <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-md">
                            <Shield className="h-6 w-6" />
                        </div>
                        <div>
                            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                Initial setup
                            </p>
                            <h1 className="font-display text-4xl leading-tight">
                                Secure your workspace with a first admin.
                            </h1>
                        </div>
                    </div>
                    <p className="max-w-xl text-lg text-muted-foreground">
                        Create the first administrator or promote an existing user. This setup
                        only runs once unless explicitly reopened by a secure token.
                    </p>
                    <div className="grid gap-3">
                        {[
                            'Create default roles and policy baselines automatically.',
                            'Assign the admin role to the first authorized account.',
                            'Lock setup when complete to prevent unauthorized changes.',
                        ].map((text) => (
                            <div
                                key={text}
                                className="flex items-start gap-3 rounded-xl border border-border/70 bg-card/70 p-4 backdrop-blur"
                            >
                                <span className="mt-1 h-2 w-2 rounded-full bg-primary" />
                                <p className="text-sm text-muted-foreground">{text}</p>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="flex flex-col items-center justify-center">
                    <Card className="w-full max-w-md">
                        <CardHeader className="space-y-1 text-center">
                            <CardTitle className="font-display text-2xl">Complete setup</CardTitle>
                            <CardDescription>
                                Create your admin account and lock down permissions.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {error && (
                                <Alert variant="destructive" className="mb-4">
                                    <AlertDescription>{error}</AlertDescription>
                                </Alert>
                            )}

                            {success && (
                                <Alert className="mb-4 border-emerald-500/40 bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-200">
                                    <AlertDescription>{success}</AlertDescription>
                                </Alert>
                            )}

                            {status?.setup_reopened && (
                                <Alert className="mb-4">
                                    <AlertDescription>
                                        Setup has been reopened. Provide the unlock token to continue.
                                    </AlertDescription>
                                </Alert>
                            )}

                            <form onSubmit={submitSetup} className="space-y-4">
                                {status?.setup_reopened && (
                                    <div className="space-y-2">
                                        <Label htmlFor="setup-token">Setup unlock token</Label>
                                        <Input
                                            id="setup-token"
                                            type="password"
                                            value={token}
                                            onChange={(event) => setToken(event.target.value)}
                                            placeholder="Paste the setup token"
                                        />
                                    </div>
                                )}

                                <Tabs
                                    value={mode}
                                    onValueChange={(value) =>
                                        setMode(value === 'promote' ? 'promote' : 'create')
                                    }
                                >
                                    <TabsList className="grid w-full grid-cols-2">
                                        <TabsTrigger value="create">Create admin</TabsTrigger>
                                        <TabsTrigger value="promote">Promote user</TabsTrigger>
                                    </TabsList>

                                    <TabsContent value="create" className="mt-4 space-y-3">
                                        <div className="space-y-2">
                                            <Label htmlFor="setup-username">Username</Label>
                                            <Input
                                                id="setup-username"
                                                value={username}
                                                onChange={(event) => setUsername(event.target.value)}
                                                placeholder="e.g., admin"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="setup-password">Password</Label>
                                            <Input
                                                id="setup-password"
                                                type="password"
                                                value={password}
                                                onChange={(event) => setPassword(event.target.value)}
                                                placeholder="Create a strong password"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="setup-confirm">Confirm password</Label>
                                            <Input
                                                id="setup-confirm"
                                                type="password"
                                                value={confirmPassword}
                                                onChange={(event) => setConfirmPassword(event.target.value)}
                                                placeholder="Confirm the password"
                                            />
                                        </div>
                                    </TabsContent>

                                    <TabsContent value="promote" className="mt-4 space-y-3">
                                        <div className="space-y-2">
                                            <Label htmlFor="existing-username">Existing username</Label>
                                            <Input
                                                id="existing-username"
                                                value={existingUsername}
                                                onChange={(event) => setExistingUsername(event.target.value)}
                                                placeholder="Enter an existing account"
                                            />
                                        </div>
                                    </TabsContent>
                                </Tabs>

                                <Button type="submit" className="w-full" disabled={isSubmitting}>
                                    {isSubmitting ? 'Completing setup...' : 'Complete setup'}
                                </Button>
                            </form>

                            <div className="mt-6 space-y-2 text-xs text-muted-foreground">
                                <div className="flex items-center gap-2">
                                    <UserPlus className="h-4 w-4" />
                                    Add admins later in the Role Management panel.
                                </div>
                                <div className="flex items-center gap-2">
                                    <KeyRound className="h-4 w-4" />
                                    Setup is locked after completion unless unlocked with a secure token.
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
