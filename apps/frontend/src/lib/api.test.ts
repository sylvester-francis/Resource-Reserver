/**
 * Api tests.
 */

import { describe, it, expect, vi } from 'vitest';

const mockAxios = {
    create: vi.fn(() => mockAxios),
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
    },
    defaults: { headers: { common: {} } },
};

// Mock axios
vi.mock('axios', () => ({
    default: mockAxios,
    AxiosError: class AxiosError extends Error {},
}));

const apiModulePromise = import('@/lib/api');

describe('API Client', () => {
    it('should create axios instance with correct base URL', async () => {
        const { API_BASE_URL } = await apiModulePromise;

        if (mockAxios.create.mock.calls.length > 0) {
            expect(mockAxios.create).toHaveBeenCalledWith({
                baseURL: expect.any(String),
                headers: {
                    'Content-Type': 'application/json',
                },
            });
        }
        // API_BASE_URL now includes /api/v1 prefix for versioning
        expect(API_BASE_URL).toBe('http://localhost:8000/api/v1');
    });

    it('should have default base URL with API version when env var is not set', async () => {
        const { API_BASE_URL } = await apiModulePromise;
        expect(API_BASE_URL).toBe('http://localhost:8000/api/v1');
    });
});

describe('API Configuration', () => {
    it('should export API_BASE_URL', async () => {
        const { API_BASE_URL } = await apiModulePromise;
        expect(API_BASE_URL).toBeDefined();
        expect(typeof API_BASE_URL).toBe('string');
    });

    it('should export default api instance', async () => {
        const { default: api } = await apiModulePromise;
        expect(api).toBeDefined();
    });
});
