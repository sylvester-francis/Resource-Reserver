/**
 * Admin roles client component.
 */

'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, Users, FileText, UserPlus, UserMinus } from 'lucide-react';
import { toast } from 'sonner';

import api from '@/lib/api';
import { useAuth } from '@/hooks/use-auth';
import type { Role } from '@/types';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { ThemeToggle } from '@/components/theme-toggle';

type RoleFormState = {
    name: string;
    description: string;
};

export default function AdminRolesClient() {
    const router = useRouter();
    const { user, loading: authLoading, isAuthenticated } = useAuth();

    const [roles, setRoles] = useState<Role[]>([]);
    const [myRoles, setMyRoles] = useState<Role[]>([]);
    const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [createRole, setCreateRole] = useState<RoleFormState>({
        name: '',
        description: '',
    });
    const [assignRole, setAssignRole] = useState({ userId: '', roleName: '' });
    const [removeRole, setRemoveRole] = useState({ userId: '', roleName: '' });
    const [actionLoading, setActionLoading] = useState(false);

    const fetchMyRoles = useCallback(async () => {
        try {
            const response = await api.get('/roles/my-roles');
            const result = Array.isArray(response.data) ? response.data : [];
            setMyRoles(result);
            setIsAdmin(result.some((role) => role.name === 'admin'));
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to load roles';
            setError(message);
            setIsAdmin(false);
        }
    }, []);

    const fetchRoles = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.get('/roles/');
            setRoles(Array.isArray(response.data) ? response.data : []);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to load roles';
            setError(
                message.toLowerCase().includes('insufficient permissions')
                    ? 'Admin access required to manage roles.'
                    : message
            );
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.replace('/login');
        }
    }, [authLoading, isAuthenticated, router]);

    useEffect(() => {
        if (!authLoading && isAuthenticated) {
            fetchMyRoles();
        }
    }, [authLoading, isAuthenticated, fetchMyRoles]);

    useEffect(() => {
        if (!authLoading && isAuthenticated && isAdmin) {
            fetchRoles();
        } else if (!authLoading && isAuthenticated) {
            setLoading(false);
        }
    }, [authLoading, isAuthenticated, isAdmin, fetchRoles]);

    const rolesByName = useMemo(() => {
        return new Set(roles.map((role) => role.name));
    }, [roles]);

    const handleCreateRole = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!createRole.name.trim()) {
            setError('Role name is required.');
            return;
        }
        setActionLoading(true);
        setError(null);
        try {
            await api.post('/roles/', {
                name: createRole.name.trim(),
                description: createRole.description.trim() || null,
            });
            toast.success('Role created successfully');
            setCreateRole({ name: '', description: '' });
            fetchRoles();
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to create role';
            setError(message);
        } finally {
            setActionLoading(false);
        }
    };

    const handleAssignRole = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!assignRole.userId.trim() || !assignRole.roleName.trim()) {
            setError('User ID and role name are required.');
            return;
        }
        setActionLoading(true);
        setError(null);
        try {
            await api.post('/roles/assign', {
                user_id: Number(assignRole.userId),
                role_name: assignRole.roleName.trim(),
            });
            toast.success('Role assigned successfully');
            setAssignRole({ userId: '', roleName: '' });
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to assign role';
            setError(message);
        } finally {
            setActionLoading(false);
        }
    };

    const handleRemoveRole = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!removeRole.userId.trim() || !removeRole.roleName.trim()) {
            setError('User ID and role name are required.');
            return;
        }
        setActionLoading(true);
        setError(null);
        try {
            await api.delete('/roles/assign', {
                data: {
                    user_id: Number(removeRole.userId),
                    role_name: removeRole.roleName.trim(),
                },
            });
            toast.success('Role removed successfully');
            setRemoveRole({ userId: '', roleName: '' });
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to remove role';
            setError(message);
        } finally {
            setActionLoading(false);
        }
    };

    return (
        <div className="min-h-screen">
            <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur">
                <div className="container mx-auto flex h-16 items-center justify-between px-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                            <Shield className="h-5 w-5" />
                        </div>
                        <div>
                            <p className="font-display text-lg">Admin Roles</p>
                            <p className="text-xs text-muted-foreground">RBAC & security</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="ghost" onClick={() => router.push('/dashboard')}>
                            Back to Dashboard
                        </Button>
                        <ThemeToggle />
                    </div>
                </div>
            </header>

            <main className="container mx-auto space-y-6 p-4 sm:p-6">
                {error && (
                    <Alert variant="destructive">
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                {isAdmin === false && (
                    <Alert>
                        <AlertDescription>
                            You are signed in without admin access. Role management actions are disabled.
                            Ask an administrator to grant the admin role to your account.
                        </AlertDescription>
                    </Alert>
                )}

                <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
                    <Card>
                        <CardHeader>
                            <CardTitle>Security Overview</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6 text-sm text-muted-foreground">
                            <div className="space-y-2">
                                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                    Authentication Methods
                                </p>
                                <ul className="space-y-1">
                                    <li>
                                        <span className="font-medium text-foreground">Username/Password:</span>{' '}
                                        Standard credential-based authentication
                                    </li>
                                    <li>
                                        <span className="font-medium text-foreground">Multi-Factor Authentication:</span>{' '}
                                        TOTP-based 2FA compatible with authenticator apps
                                    </li>
                                    <li>
                                        <span className="font-medium text-foreground">OAuth2:</span>{' '}
                                        Authorization code and client credentials flows
                                    </li>
                                </ul>
                            </div>
                            <div className="space-y-2">
                                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                    OAuth2 Scopes
                                </p>
                                <div className="flex flex-wrap gap-2">
                                    {[
                                        'read: View resources and reservations',
                                        'write: Create and modify resources and reservations',
                                        'delete: Remove resources and reservations',
                                        'admin: Administrative access',
                                        'user:profile: Access user profile information',
                                    ].map((scope) => (
                                        <Badge key={scope} variant="secondary">
                                            {scope}
                                        </Badge>
                                    ))}
                                </div>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                For complete security documentation, see <code>docs/auth-guide.md</code>.
                            </p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Role-Based Access Control</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="overflow-x-auto rounded-xl border border-border/70">
                                <table className="min-w-full text-left text-sm">
                                    <thead className="bg-muted/60 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                                        <tr>
                                            <th className="px-4 py-3">Role</th>
                                            <th className="px-4 py-3">Resources</th>
                                            <th className="px-4 py-3">Reservations</th>
                                            <th className="px-4 py-3">Users</th>
                                            <th className="px-4 py-3">OAuth2</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border/70">
                                        {[
                                            ['Admin', 'Full control', 'Full control', 'Full control', 'Full control'],
                                            ['User', 'Read only', 'Create/manage own', 'Read only', 'Manage own clients'],
                                            ['Guest', 'Read only', 'None', 'None', 'None'],
                                        ].map((row) => (
                                            <tr key={row[0]}>
                                                {row.map((cell, cellIdx) => (
                                                    <td key={cellIdx} className="px-4 py-3 text-sm text-foreground">
                                                        {cell}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <div className="grid gap-6 lg:grid-cols-3">
                    <Card>
                        <CardHeader className="flex items-center justify-between gap-2">
                            <div>
                                <CardTitle>Roles Directory</CardTitle>
                                <p className="text-sm text-muted-foreground">
                                    {isAdmin ? `${roles.length} role${roles.length === 1 ? '' : 's'} found` : 'Admin access required'}
                                </p>
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={fetchRoles}
                                disabled={loading || !isAdmin}
                            >
                                Refresh
                            </Button>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {loading ? (
                                <div className="space-y-3">
                                    {[...Array(3)].map((_, i) => (
                                        <Skeleton key={i} className="h-12 w-full" />
                                    ))}
                                </div>
                            ) : !isAdmin ? (
                                <p className="text-sm text-muted-foreground">
                                    Admin access is required to view the roles directory.
                                </p>
                            ) : roles.length === 0 ? (
                                <p className="text-sm text-muted-foreground">
                                    No roles available. Create one to get started.
                                </p>
                            ) : (
                                <div className="space-y-2">
                                    {roles.map((role) => (
                                        <div
                                            key={role.id}
                                            className="flex items-center justify-between rounded-xl border border-border/70 bg-card/70 px-4 py-3"
                                        >
                                            <div>
                                                <p className="text-sm font-semibold text-foreground">
                                                    {role.name}
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    {role.description || 'No description'}
                                                </p>
                                            </div>
                                            <Badge variant="outline">#{role.id}</Badge>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <form onSubmit={handleCreateRole} className="space-y-3 pt-2">
                                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                    <FileText className="h-4 w-4" />
                                    Create role
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="role-name">Role name</Label>
                                    <Input
                                        id="role-name"
                                        value={createRole.name}
                                        onChange={(event) =>
                                            setCreateRole((prev) => ({ ...prev, name: event.target.value }))
                                        }
                                        placeholder="e.g., admin"
                                        disabled={!isAdmin}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="role-description">Description</Label>
                                    <Input
                                        id="role-description"
                                        value={createRole.description}
                                        onChange={(event) =>
                                            setCreateRole((prev) => ({
                                                ...prev,
                                                description: event.target.value,
                                            }))
                                        }
                                        placeholder="Role capabilities and scope"
                                        disabled={!isAdmin}
                                    />
                                </div>
                                <Button type="submit" disabled={actionLoading || !isAdmin}>
                                    Create role
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Assign Role</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleAssignRole} className="space-y-4">
                                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                    <UserPlus className="h-4 w-4" />
                                    Assignment
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="assign-user">User ID</Label>
                                    <Input
                                        id="assign-user"
                                        value={assignRole.userId}
                                        onChange={(event) =>
                                            setAssignRole((prev) => ({ ...prev, userId: event.target.value }))
                                        }
                                        placeholder="e.g., 12"
                                        disabled={!isAdmin}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="assign-role">Role name</Label>
                                    <Input
                                        id="assign-role"
                                        value={assignRole.roleName}
                                        onChange={(event) =>
                                            setAssignRole((prev) => ({ ...prev, roleName: event.target.value }))
                                        }
                                        placeholder="e.g., admin"
                                        disabled={!isAdmin}
                                    />
                                    {!rolesByName.has(assignRole.roleName.trim()) && assignRole.roleName.trim() ? (
                                        <p className="text-xs text-muted-foreground">
                                            Role not found in directory. Check spelling or create it.
                                        </p>
                                    ) : null}
                                </div>
                                <Button type="submit" disabled={actionLoading || !isAdmin}>
                                    Assign role
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Remove Role</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleRemoveRole} className="space-y-4">
                                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                    <UserMinus className="h-4 w-4" />
                                    Revocation
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="remove-user">User ID</Label>
                                    <Input
                                        id="remove-user"
                                        value={removeRole.userId}
                                        onChange={(event) =>
                                            setRemoveRole((prev) => ({ ...prev, userId: event.target.value }))
                                        }
                                        placeholder="e.g., 12"
                                        disabled={!isAdmin}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="remove-role">Role name</Label>
                                    <Input
                                        id="remove-role"
                                        value={removeRole.roleName}
                                        onChange={(event) =>
                                            setRemoveRole((prev) => ({ ...prev, roleName: event.target.value }))
                                        }
                                        placeholder="e.g., guest"
                                        disabled={!isAdmin}
                                    />
                                </div>
                                <Button type="submit" variant="outline" disabled={actionLoading || !isAdmin}>
                                    Remove role
                                </Button>
                            </form>
                        </CardContent>
                    </Card>
                </div>

                <Card>
                    <CardHeader className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <CardTitle>Access Notes</CardTitle>
                            <p className="text-sm text-muted-foreground">
                                Roles are enforced by the API. Admin access is required for changes.
                            </p>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Users className="h-4 w-4" />
                            Signed in as {user?.username ?? 'Unknown'} · Roles:{' '}
                            {myRoles.length ? myRoles.map((role) => role.name).join(', ') : 'None'}
                        </div>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground">
                        {isAdmin ? (
                            <>
                                Use this panel to keep your authorization rules clean and auditable.
                                Assign roles carefully and verify changes in the audit log.
                            </>
                        ) : (
                            <>
                                To bootstrap admin access, sign in with an existing admin account or ask an
                                administrator to run `cli roles assign &lt;user_id&gt; admin`. If no admin
                                exists yet, you can assign one directly in the database.
                            </>
                        )}
                    </CardContent>
                </Card>
            </main>
        </div>
    );
}
