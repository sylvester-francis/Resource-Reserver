'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Calendar } from 'lucide-react';
import { toast } from 'sonner';

import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ThemeToggle } from '@/components/theme-toggle';
import { Skeleton } from '@/components/ui/skeleton';

function LoginContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { login, register } = useAuth();

    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(searchParams?.get('error') ?? null);
    const [success, setSuccess] = useState<string | null>(searchParams?.get('success') ?? null);
    const [showMfaInput, setShowMfaInput] = useState(false);
    const [pendingCredentials, setPendingCredentials] = useState<{ username: string; password: string } | null>(null);

    // Form states
    const [loginUsername, setLoginUsername] = useState('');
    const [loginPassword, setLoginPassword] = useState('');
    const [mfaCode, setMfaCode] = useState('');
    const [registerUsername, setRegisterUsername] = useState('');
    const [registerPassword, setRegisterPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            await login(loginUsername, loginPassword, showMfaInput ? mfaCode : undefined);
            toast.success('Welcome back!');
            router.push('/dashboard');
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Login failed';

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

        if (registerPassword.length < 6) {
            setError('Password must be at least 6 characters');
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
            setError(err instanceof Error ? err.message : 'Registration failed');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 px-4">
            <div className="absolute right-4 top-4">
                <ThemeToggle />
            </div>

            <Card className="w-full max-w-md">
                <CardHeader className="space-y-1 text-center">
                    <div className="mb-2 flex justify-center">
                        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600">
                            <Calendar className="h-6 w-6 text-white" />
                        </div>
                    </div>
                    <CardTitle className="text-2xl font-bold">Resource Reserver</CardTitle>
                    <CardDescription>
                        {showMfaInput
                            ? 'Enter your authentication code'
                            : 'Sign in to your account or create a new one'
                        }
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {error && (
                        <Alert variant="destructive" className="mb-4">
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    {success && (
                        <Alert className="mb-4 border-green-500 bg-green-50 text-green-700">
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
                                    className="text-center text-2xl tracking-widest"
                                    autoFocus
                                    required
                                />
                                <p className="text-xs text-gray-500">
                                    Enter the code from your authenticator app or use a backup code
                                </p>
                            </div>
                            <div className="flex gap-2">
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
                        <Tabs defaultValue="login" className="w-full" onValueChange={() => {
                            setError(null);
                            setSuccess(null);
                        }}>
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
    );
}

function LoginFallback() {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 px-4">
            <Card className="w-full max-w-md">
                <CardHeader className="space-y-1 text-center">
                    <Skeleton className="h-12 w-12 rounded-full mx-auto" />
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
