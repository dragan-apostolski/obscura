import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "pub-83751d58d6b3424681fe2e8013206003.r2.dev",
        pathname: "/products/**",
      },
    ],
  },
};

export default nextConfig;
