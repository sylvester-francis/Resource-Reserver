/**
 * Next.js Configuration
 * 
 * API Proxy Mode:
 * When NEXT_PUBLIC_API_URL is empty (recommended for Docker/enterprise deployments),
 * all /api/* requests are proxied through Next.js rewrites to the backend.
 * This avoids CORS issues and works with corporate HTTP proxies.
 * 
 * The INTERNAL_API_URL environment variable specifies where the Next.js server
 * should forward requests (defaults to http://backend:8000 for Docker networking).
 */

import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
    // Required for Docker deployment
    output: 'standalone',

    images: {
        remotePatterns: [],
    },

    // API Proxy: Forward /api/*, /health, /ws to backend when using relative URLs
    // This enables enterprise deployments where browsers cannot reach backend directly
    async rewrites() {
        const apiUrl = process.env.INTERNAL_API_URL || 'http://backend:8000';
        return [
            {
                source: '/api/:path*',
                destination: `${apiUrl}/api/:path*`,
            },
            {
                source: '/health',
                destination: `${apiUrl}/health`,
            },
            {
                source: '/ws',
                destination: `${apiUrl}/ws`,
            },
        ];
    },
};

export default withNextIntl(nextConfig);
