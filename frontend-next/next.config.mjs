import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
    // Required for Docker deployment
    output: 'standalone',

    images: {
        remotePatterns: [],
    },
};

export default withNextIntl(nextConfig);
