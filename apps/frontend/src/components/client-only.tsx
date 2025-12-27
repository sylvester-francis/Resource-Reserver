/**
 * Client only component.
 */

'use client';

import dynamic from 'next/dynamic';
import type { ReactNode } from 'react';

/**
 * ClientOnly wrapper component to prevent SSR for children.
 * This is needed because some components (like Radix UI primitives)
 * don't work properly during static generation.
 */
export function ClientOnly({ children }: { children: ReactNode }) {
    return <>{children}</>;
}

/**
 * Create a client-only version of any component
 */
export function createClientComponent<P extends object>(
    Component: React.ComponentType<P>
) {
    return dynamic(() => Promise.resolve(Component), {
        ssr: false,
    });
}
