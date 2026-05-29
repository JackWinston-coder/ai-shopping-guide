/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8010',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/data/:path*',
        destination: '/api/static/:path*',
      },
    ]
  },
}

export default nextConfig
