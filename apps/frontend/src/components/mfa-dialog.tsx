/**
 * Mfa dialog component.
 */

'use client';

import { useState } from 'react';
import { Shield, Copy, Eye, EyeOff, RefreshCw, Check } from 'lucide-react';
import { toast } from 'sonner';

import api from '@/lib/api';
import type { User, MFASetupResponse } from '@/types';

import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';

interface MfaDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    user: User | null;
}

export function MfaDialog({ open, onOpenChange, user }: MfaDialogProps) {
    const [step, setStep] = useState<'overview' | 'setup' | 'backup_codes'>('overview');
    const [setupData, setSetupData] = useState<MFASetupResponse | null>(null);
    const [backupCodes, setBackupCodes] = useState<string[]>([]);
    const [verificationCode, setVerificationCode] = useState('');
    const [disablePassword, setDisablePassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [showCodes, setShowCodes] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSetupMfa = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await api.post('/auth/mfa/setup');
            setSetupData(response.data);
            setStep('setup');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to start MFA setup');
        } finally {
            setIsLoading(false);
        }
    };

    const handleEnableMfa = async () => {
        if (!verificationCode || verificationCode.length !== 6) {
            setError('Please enter a valid 6-digit code');
            return;
        }

        setIsLoading(true);
        setError(null);
        try {
            await api.post('/auth/mfa/verify', { code: verificationCode });
            toast.success('MFA enabled successfully!');
            if (setupData?.backup_codes) {
                setBackupCodes(setupData.backup_codes);
                setStep('backup_codes');
            } else {
                onOpenChange(false);
                window.location.reload();
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Invalid verification code');
        } finally {
            setIsLoading(false);
        }
    };

    const handleDisableMfa = async () => {
        if (!disablePassword) {
            setError('Please enter your password');
            return;
        }

        setIsLoading(true);
        setError(null);
        try {
            await api.post('/auth/mfa/disable', { password: disablePassword });
            toast.success('MFA disabled');
            onOpenChange(false);
            window.location.reload();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Invalid password');
        } finally {
            setIsLoading(false);
        }
    };

    const handleRegenerateBackupCodes = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await api.post('/auth/mfa/backup-codes');
            setBackupCodes(response.data.backup_codes);
            setStep('backup_codes');
            toast.success('New backup codes generated');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to generate backup codes');
        } finally {
            setIsLoading(false);
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        toast.success('Copied to clipboard');
    };

    const resetDialog = () => {
        setStep('overview');
        setSetupData(null);
        setBackupCodes([]);
        setVerificationCode('');
        setDisablePassword('');
        setError(null);
        setShowCodes(false);
    };

    return (
        <Dialog open={open} onOpenChange={(open) => {
            if (!open) resetDialog();
            onOpenChange(open);
        }}>
            <DialogContent className="sm:max-w-[450px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Shield className="h-5 w-5" />
                        Security Settings
                    </DialogTitle>
                    <DialogDescription>
                        Manage your two-factor authentication settings.
                    </DialogDescription>
                </DialogHeader>

                {error && (
                    <Alert variant="destructive">
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                {step === 'overview' && (
                    <div className="space-y-4">
                        <div className="rounded-lg border p-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h4 className="font-medium">Two-Factor Authentication</h4>
                                    <p className="text-sm text-muted-foreground">
                                        {user?.mfa_enabled
                                            ? 'Your account is protected with MFA'
                                            : 'Add an extra layer of security'}
                                    </p>
                                </div>
                                <div className={`rounded-full px-3 py-1 text-xs font-medium ${user?.mfa_enabled
                                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                        : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                                    }`}>
                                    {user?.mfa_enabled ? 'Enabled' : 'Disabled'}
                                </div>
                            </div>
                        </div>

                        {user?.mfa_enabled ? (
                            <div className="space-y-3">
                                <Button
                                    variant="outline"
                                    className="w-full"
                                    onClick={handleRegenerateBackupCodes}
                                    disabled={isLoading}
                                >
                                    <RefreshCw className="mr-2 h-4 w-4" />
                                    Regenerate Backup Codes
                                </Button>

                                <Separator />

                                <div className="space-y-2">
                                    <Label htmlFor="disable-password">Enter password to disable MFA</Label>
                                    <div className="flex gap-2">
                                        <Input
                                            id="disable-password"
                                            type="password"
                                            placeholder="Account password"
                                            value={disablePassword}
                                            onChange={(e) => setDisablePassword(e.target.value)}
                                        />
                                        <Button
                                            variant="destructive"
                                            onClick={handleDisableMfa}
                                            disabled={isLoading}
                                        >
                                            Disable
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <Button onClick={handleSetupMfa} disabled={isLoading} className="w-full">
                                {isLoading ? 'Setting up...' : 'Enable Two-Factor Authentication'}
                            </Button>
                        )}
                    </div>
                )}

                {step === 'setup' && setupData && (
                    <div className="space-y-4">
                        <div className="text-center">
                            <p className="text-sm text-muted-foreground mb-4">
                                Scan this QR code with your authenticator app
                            </p>
                            {setupData.qr_code && (
                                <div className="inline-block rounded-lg bg-white p-4">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                        src={setupData.qr_code}
                                        alt="MFA QR Code"
                                        className="h-48 w-48"
                                    />
                                </div>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label>Manual entry code</Label>
                            <div className="flex gap-2">
                                <Input
                                    value={setupData.secret}
                                    readOnly
                                    className="font-mono text-sm"
                                />
                                <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={() => copyToClipboard(setupData.secret)}
                                >
                                    <Copy className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>

                        <Separator />

                        <div className="space-y-2">
                            <Label htmlFor="verify-code">Enter verification code</Label>
                            <Input
                                id="verify-code"
                                type="text"
                                placeholder="Enter 6-digit code"
                                value={verificationCode}
                                onChange={(e) => setVerificationCode(e.target.value)}
                                maxLength={6}
                                className="text-center text-lg tracking-widest"
                            />
                        </div>

                        <DialogFooter>
                            <Button variant="outline" onClick={() => setStep('overview')}>
                                Back
                            </Button>
                            <Button onClick={handleEnableMfa} disabled={isLoading}>
                                {isLoading ? 'Verifying...' : 'Verify & Enable'}
                            </Button>
                        </DialogFooter>
                    </div>
                )}

                {step === 'backup_codes' && (
                    <div className="space-y-4">
                        <Alert>
                            <AlertDescription>
                                <strong>Save these backup codes!</strong> Each code can only be used once.
                                Store them in a safe place.
                            </AlertDescription>
                        </Alert>

                        <div className="rounded-lg border p-4">
                            <div className="flex items-center justify-between mb-3">
                                <span className="text-sm font-medium">Backup Codes</span>
                                <div className="flex gap-1">
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => setShowCodes(!showCodes)}
                                    >
                                        {showCodes ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => copyToClipboard(backupCodes.join('\n'))}
                                    >
                                        <Copy className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                {backupCodes.map((code, idx) => (
                                    <code
                                        key={idx}
                                        className="rounded bg-muted px-2 py-1 text-sm font-mono"
                                    >
                                        {showCodes ? code : '••••••••'}
                                    </code>
                                ))}
                            </div>
                        </div>

                        <DialogFooter>
                            <Button onClick={() => {
                                onOpenChange(false);
                                window.location.reload();
                            }}>
                                <Check className="mr-2 h-4 w-4" />
                                Done
                            </Button>
                        </DialogFooter>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
