/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone", // 產出最小化獨立伺服器，供 Docker 部署
};

export default nextConfig;
