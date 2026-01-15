/**
 * Next.js Middleware
 * 
 * Handles server-side routing logic (runs on the Next.js server, not browser).
 * Uses INTERNAL_API_URL for direct container-to-container communication in Docker,
 * bypassing the browser proxy path entirely.
 * 
 * Configuration priority:
 * 1. INTERNAL_API_URL - Docker container networking (e.g., http://backend:8000)
 * 2. NEXT_PUBLIC_API_URL - Direct URL if set
 * 3. http://localhost:8000 - Local development fallback
 */

import { NextRequest, NextResponse } from 'next/server';

// Server-side API URL for middleware (container-to-container in Docker)
const API_BASE_URL = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function middleware(request: NextRequest) {
    if (request.nextUrl.pathname !== '/') {
        return NextResponse.next();
    }

    try {
        const setupResponse = await fetch(`${API_BASE_URL}/setup/status`, { cache: 'no-store' });
        if (setupResponse.ok) {
            const status = await setupResponse.json();
            if (status?.user_count === 0 || !status?.setup_complete) {
                return NextResponse.redirect(new URL('/setup', request.url));
            }
        }
    } catch {
        return NextResponse.next();
    }

    const token = request.cookies.get('auth_token')?.value;
    if (!token) {
        return NextResponse.redirect(new URL('/login', request.url));
    }

    try {
        const authResponse = await fetch(`${API_BASE_URL}/users/me`, {
            cache: 'no-store',
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (authResponse.ok) {
            return NextResponse.redirect(new URL('/dashboard', request.url));
        }
    } catch {
        return NextResponse.redirect(new URL('/login', request.url));
    }

    return NextResponse.redirect(new URL('/login', request.url));
}

export const config = {
    matcher: ['/'],
};
