/** @type {import('next').NextConfig} */
const nextConfig = {
    // Required for Docker deployment
    output: 'standalone',

    images: {
        remotePatterns: [],
    },
};

module.exports = nextConfig;
