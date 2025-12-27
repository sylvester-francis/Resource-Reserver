/**
 * Login client component.
 */

'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Calendar } from 'lucide-react';
import { toast } from 'sonner';

import { useAuth } from '@/hooks/use-auth';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ThemeToggle } from '@/components/theme-toggle';
import { Skeleton } from '@/components/ui/skeleton';
import { PasswordStrengthMeter } from '@/components/password-strength-meter';

const getErrorMessage = (err: unknown, fallback: string) => {
    if (err && typeof err === 'object') {
        const response = (err as { response?: { data?: { detail?: string; message?: string } } }).response;
        const detail = response?.data?.detail ?? response?.data?.message;
        if (detail) {
            return String(detail);
        }
    }
    if (err instanceof Error) {
        return err.message;
    }
    return fallback;
};

function LoginContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { login, register } = useAuth();

    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(searchParams?.get('error') ?? null);
    const [success, setSuccess] = useState<string | null>(searchParams?.get('success') ?? null);
    const [showMfaInput, setShowMfaInput] = useState(false);
    const [pendingCredentials, setPendingCredentials] = useState<{ username: string; password: string } | null>(null);
    const [setupChecked, setSetupChecked] = useState(false);

    // Form states
    const [loginUsername, setLoginUsername] = useState('');
    const [loginPassword, setLoginPassword] = useState('');
    const [mfaCode, setMfaCode] = useState('');
    const [registerUsername, setRegisterUsername] = useState('');
    const [registerPassword, setRegisterPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    useEffect(() => {
        let active = true;
        const checkSetup = async () => {
            try {
                const response = await api.get('/setup/status');
                if (!active) return;
                const count =
                    typeof response.data?.user_count === 'number' ? response.data.user_count : null;
                if (count === 0 || !response.data?.setup_complete) {
                    router.replace('/setup');
                    return;
                }
            } catch {
                // Fall back to login if setup check fails.
            } finally {
                if (active) setSetupChecked(true);
            }
        };
        checkSetup();
        return () => {
            active = false;
        };
    }, [router]);

    if (!setupChecked) {
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

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            await login(loginUsername, loginPassword, showMfaInput ? mfaCode : undefined);
            toast.success('Welcome back!');
            router.push('/dashboard');
        } catch (err) {
            const message = getErrorMessage(err, 'Login failed');

            // Check if MFA is required
            if (message.toLowerCase().includes('mfa') || message.toLowerCase().includes('2fa')) {
                setShowMfaInput(true);
                setPendingCredentials({ username: loginUsername, password: loginPassword });
                setError('Please enter your MFA code');
            } else {
                setError(message);
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleMfaSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!pendingCredentials) return;

        setError(null);
        setIsLoading(true);

        try {
            await login(pendingCredentials.username, pendingCredentials.password, mfaCode);
            toast.success('Welcome back!');
            router.push('/dashboard');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Invalid MFA code');
        } finally {
            setIsLoading(false);
        }
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (registerPassword !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        // Password policy validation (matches backend)
        const passwordErrors: string[] = [];
        if (registerPassword.length < 8) {
            passwordErrors.push('Password must be at least 8 characters');
        }
        if (!/[A-Z]/.test(registerPassword)) {
            passwordErrors.push('Password must contain an uppercase letter');
        }
        if (!/[a-z]/.test(registerPassword)) {
            passwordErrors.push('Password must contain a lowercase letter');
        }
        if (!/\d/.test(registerPassword)) {
            passwordErrors.push('Password must contain a number');
        }
        if (!/[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;'/`~]/.test(registerPassword)) {
            passwordErrors.push('Password must contain a special character');
        }
        if (registerUsername && registerUsername.length >= 3) {
            if (registerPassword.toLowerCase().includes(registerUsername.toLowerCase())) {
                passwordErrors.push('Password cannot contain your username');
            }
        }

        if (passwordErrors.length > 0) {
            setError(passwordErrors.join('; '));
            return;
        }

        setIsLoading(true);

        try {
            await register(registerUsername, registerPassword);
            setSuccess('Registration successful! Please sign in.');
            setRegisterUsername('');
            setRegisterPassword('');
            setConfirmPassword('');
            toast.success('Account created successfully!');
        } catch (err) {
            setError(getErrorMessage(err, 'Registration failed'));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen overflow-hidden">
            <div className="pointer-events-none absolute -top-40 right-[-10%] h-[420px] w-[420px] rounded-full bg-primary/15 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-40 left-[-10%] h-[360px] w-[360px] rounded-full bg-secondary/50 blur-3xl" />
            <div className="absolute right-6 top-6 z-10">
                <ThemeToggle />
            </div>

            <div className="container mx-auto grid min-h-screen items-center gap-12 px-4 py-12 lg:grid-cols-[1.1fr_0.9fr]">
                <div className="hidden flex-col gap-8 lg:flex lg:pr-10">
                    <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-md">
                            <Calendar className="h-6 w-6" />
                        </div>
                        <div>
                            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                Resource Reserver
                            </p>
                            <h1 className="font-display text-4xl leading-tight">
                                Scheduling clarity for high-demand teams.
                            </h1>
                        </div>
                    </div>
                    <p className="max-w-xl text-lg text-muted-foreground">
                        Keep every room, device, and shared asset in sync. See availability at a
                        glance, reserve confidently, and keep stakeholders aligned.
                    </p>
                    <div className="grid gap-3">
                        {[
                            'Unified availability across teams and locations.',
                            'Live status, history, and audit-ready records.',
                            'Instant setup with CSV imports and smart filters.',
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
                    <div className="flex flex-wrap gap-6 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                        <span>Secure</span>
                        <span>Auditable</span>
                        <span>Responsive</span>
                    </div>
                </div>

                <div className="flex flex-col items-center justify-center">
                    <div className="mb-6 flex flex-col items-center gap-2 text-center lg:hidden">
                        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-md">
                            <Calendar className="h-6 w-6" />
                        </div>
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                            Resource Reserver
                        </p>
                        <h1 className="font-display text-3xl">Scheduling clarity for teams.</h1>
                    </div>

                    <Card className="w-full max-w-md">
                        <CardHeader className="space-y-1 text-center">
                            <CardTitle className="font-display text-2xl">
                                {showMfaInput ? 'Verify your login' : 'Welcome back'}
                            </CardTitle>
                            <CardDescription>
                                {showMfaInput
                                    ? 'Enter your authentication code to continue.'
                                    : 'Sign in to your account or create a new one.'}
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

                            {showMfaInput ? (
                                <form onSubmit={handleMfaSubmit} className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="mfa-code">Authentication Code</Label>
                                        <Input
                                            id="mfa-code"
                                            type="text"
                                            placeholder="Enter 6-digit code"
                                            value={mfaCode}
                                            onChange={(e) => setMfaCode(e.target.value)}
                                            maxLength={6}
                                            className="text-center text-2xl tracking-[0.35em]"
                                            autoFocus
                                            required
                                        />
                                        <p className="text-xs text-muted-foreground">
                                            Use the code from your authenticator app.
                                        </p>
                                    </div>
                                    <div className="flex flex-col gap-2 sm:flex-row">
                                        <Button
                                            type="button"
                                            variant="outline"
                                            className="flex-1"
                                            onClick={() => {
                                                setShowMfaInput(false);
                                                setMfaCode('');
                                                setPendingCredentials(null);
                                                setError(null);
                                            }}
                                        >
                                            Back
                                        </Button>
                                        <Button type="submit" className="flex-1" disabled={isLoading}>
                                            {isLoading ? 'Verifying...' : 'Verify'}
                                        </Button>
                                    </div>
                                </form>
                            ) : (
                                <Tabs
                                    defaultValue="login"
                                    className="w-full"
                                    onValueChange={() => {
                                        setError(null);
                                        setSuccess(null);
                                    }}
                                >
                                    <TabsList className="grid w-full grid-cols-2">
                                        <TabsTrigger value="login">Sign In</TabsTrigger>
                                        <TabsTrigger value="register">Register</TabsTrigger>
                                    </TabsList>

                                    <TabsContent value="login" className="mt-4">
                                        <form onSubmit={handleLogin} className="space-y-4">
                                            <div className="space-y-2">
                                                <Label htmlFor="login-username">Username</Label>
                                                <Input
                                                    id="login-username"
                                                    type="text"
                                                    placeholder="Enter your username"
                                                    value={loginUsername}
                                                    onChange={(e) => setLoginUsername(e.target.value)}
                                                    required
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="login-password">Password</Label>
                                                <Input
                                                    id="login-password"
                                                    type="password"
                                                    placeholder="Enter your password"
                                                    value={loginPassword}
                                                    onChange={(e) => setLoginPassword(e.target.value)}
                                                    required
                                                />
                                            </div>
                                            <Button type="submit" className="w-full" disabled={isLoading}>
                                                {isLoading ? 'Signing in...' : 'Sign In'}
                                            </Button>
                                        </form>
                                    </TabsContent>

                                    <TabsContent value="register" className="mt-4">
                                        <form onSubmit={handleRegister} className="space-y-4">
                                            <div className="space-y-2">
                                                <Label htmlFor="register-username">Username</Label>
                                                <Input
                                                    id="register-username"
                                                    type="text"
                                                    placeholder="Choose a username"
                                                    value={registerUsername}
                                                    onChange={(e) => setRegisterUsername(e.target.value)}
                                                    required
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="register-password">Password</Label>
                                                <Input
                                                    id="register-password"
                                                    type="password"
                                                    placeholder="Choose a password"
                                                    value={registerPassword}
                                                    onChange={(e) => setRegisterPassword(e.target.value)}
                                                    required
                                                />
                                                <PasswordStrengthMeter password={registerPassword} />
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="confirm-password">Confirm Password</Label>
                                                <Input
                                                    id="confirm-password"
                                                    type="password"
                                                    placeholder="Confirm your password"
                                                    value={confirmPassword}
                                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                                    required
                                                />
                                            </div>
                                            <Button type="submit" className="w-full" disabled={isLoading}>
                                                {isLoading ? 'Creating account...' : 'Create Account'}
                                            </Button>
                                        </form>
                                    </TabsContent>
                                </Tabs>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}

function LoginFallback() {
    return (
        <div className="flex min-h-screen items-center justify-center px-4">
            <Card className="w-full max-w-md">
                <CardHeader className="space-y-2 text-center">
                    <Skeleton className="h-12 w-12 rounded-2xl mx-auto" />
                    <Skeleton className="h-8 w-48 mx-auto" />
                    <Skeleton className="h-4 w-64 mx-auto" />
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

export default function LoginClient() {
    return (
        <Suspense fallback={<LoginFallback />}>
            <LoginContent />
        </Suspense>
    );
}
