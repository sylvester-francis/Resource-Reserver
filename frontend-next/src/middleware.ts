import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
