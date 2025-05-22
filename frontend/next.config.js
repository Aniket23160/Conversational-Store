/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    images: {
      domains: ['localhost'],
      unoptimized: true,
    },
    async rewrites() {
      return [
        {
          source: '/api/placeholder/:path*',
          destination: 'https://via.placeholder.com/:path*',
        },
      ]
    },
  }
  
  module.exports = nextConfig