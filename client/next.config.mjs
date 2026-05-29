const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
        destination: `${API_URL}/data/:path*`,
      },
    ]
  },
}

export default nextConfig
