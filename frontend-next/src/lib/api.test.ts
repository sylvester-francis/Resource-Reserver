import { describe, it, expect, beforeEach, vi } from 'vitest';
import axios from 'axios';

// Mock axios
vi.mock('axios', () => {
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
    return { default: mockAxios, AxiosError: class AxiosError extends Error { } };
});

describe('API Client', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Reset module registry to get fresh import
        vi.resetModules();
    });

    it('should create axios instance with correct base URL', async () => {
        // Import fresh after mocks are set
        const { default: api, API_BASE_URL } = await import('@/lib/api');

        expect(axios.create).toHaveBeenCalledWith({
            baseURL: expect.any(String),
            headers: {
                'Content-Type': 'application/json',
            },
        });
        expect(API_BASE_URL).toBe('http://localhost:8000');
    });

    it('should have default base URL when env var is not set', async () => {
        const { API_BASE_URL } = await import('@/lib/api');
        expect(API_BASE_URL).toBe('http://localhost:8000');
    });
});

describe('API Configuration', () => {
    it('should export API_BASE_URL', async () => {
        const { API_BASE_URL } = await import('@/lib/api');
        expect(API_BASE_URL).toBeDefined();
        expect(typeof API_BASE_URL).toBe('string');
    });

    it('should export default api instance', async () => {
        const { default: api } = await import('@/lib/api');
        expect(api).toBeDefined();
    });
});
