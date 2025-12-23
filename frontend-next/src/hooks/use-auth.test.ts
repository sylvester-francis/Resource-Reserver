import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import * as auth from '@/hooks/use-auth';
import { ensureDom } from '../test/ensure-dom';

// Mock the API module
vi.mock('@/lib/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
    },
}));

// Get the mocked module
import api from '@/lib/api';

const apiMock = api as {
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
};

describe('useAuth Hook', () => {
    beforeAll(() => {
        ensureDom();
    });

    beforeEach(() => {
        vi.clearAllMocks();
        // Clear cookies
        document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    });

    describe('Initial State', () => {
        it('should start with loading true and no user', async () => {
            apiMock.get.mockRejectedValueOnce(new Error('Not authenticated'));

            const { result } = renderHook(() => auth.useAuth());

            expect(result.current.loading).toBe(true);
            expect(result.current.user).toBe(null);

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });
        });

        it('should check auth on mount', async () => {
            apiMock.get.mockResolvedValueOnce({
                data: { id: 1, username: 'testuser' },
            });

            const { result } = renderHook(() => auth.useAuth());

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            expect(api.get).toHaveBeenCalledWith('/users/me');
        });
    });

    describe('Authentication', () => {
        it('should set user when checkAuth succeeds', async () => {
            const mockUser = { id: 1, username: 'testuser', is_admin: false };
            apiMock.get.mockResolvedValueOnce({ data: mockUser });

            const { result } = renderHook(() => auth.useAuth());

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            expect(result.current.user).toEqual(mockUser);
            expect(result.current.isAuthenticated).toBe(true);
        });

        it('should clear user when checkAuth fails', async () => {
            apiMock.get.mockRejectedValueOnce(new Error('Unauthorized'));

            const { result } = renderHook(() => auth.useAuth());

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            expect(result.current.user).toBe(null);
            expect(result.current.isAuthenticated).toBe(false);
        });
    });

    describe('Login', () => {
        it('should send login request with credentials', async () => {
            apiMock.get.mockRejectedValueOnce(new Error('Not authenticated'));
            apiMock.post.mockResolvedValueOnce({
                data: { access_token: 'test-token' },
            });
            apiMock.get.mockResolvedValueOnce({
                data: { id: 1, username: 'testuser' },
            });

            const { result } = renderHook(() => auth.useAuth());

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            await act(async () => {
                await result.current.login('testuser', 'password123');
            });

            expect(api.post).toHaveBeenCalledWith(
                '/token',
                expect.any(URLSearchParams),
                { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
            );
        });

        it('should include MFA code when provided', async () => {
            apiMock.get.mockRejectedValueOnce(new Error('Not authenticated'));
            apiMock.post.mockResolvedValueOnce({
                data: { access_token: 'test-token' },
            });
            apiMock.get.mockResolvedValueOnce({
                data: { id: 1, username: 'testuser' },
            });

            const { result } = renderHook(() => auth.useAuth());

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            await act(async () => {
                await result.current.login('testuser', 'password123', '123456');
            });

            const formDataCall = apiMock.post.mock.calls[0][1] as URLSearchParams;
            expect(formDataCall.get('mfa_code')).toBe('123456');
        });
    });

    describe('Register', () => {
        it('should send register request', async () => {
            apiMock.get.mockRejectedValueOnce(new Error('Not authenticated'));
            apiMock.post.mockResolvedValueOnce({
                data: { id: 1, username: 'newuser' },
            });

            const { result } = renderHook(() => auth.useAuth());

            await waitFor(() => {
                expect(result.current.loading).toBe(false);
            });

            await act(async () => {
                await result.current.register('newuser', 'password123');
            });

            expect(api.post).toHaveBeenCalledWith('/register', {
                username: 'newuser',
                password: 'password123',
            });
        });
    });

    describe('Logout', () => {
        it('should clear user on logout', async () => {
            apiMock.get.mockResolvedValueOnce({
                data: { id: 1, username: 'testuser' },
            });
            // Mock logout API call
            apiMock.post.mockResolvedValueOnce({
                data: { message: 'Successfully logged out', revoked_tokens: 1 },
            });
            window.history.replaceState({}, '', '/');

            const { result } = renderHook(() => auth.useAuth());

            await waitFor(() => {
                expect(result.current.isAuthenticated).toBe(true);
            });

            // logout is now async
            await act(async () => {
                await result.current.logout();
            });

            expect(result.current.user).toBe(null);
            expect(window.location.pathname).toBe('/login');
        });
    });
});
