import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ['three', 'three-stdlib', '@react-three/fiber', '@react-three/drei'],
};

export default nextConfig;
