/** @type {import("next").NextConfig} */
const nextConfig = {
  basePath: '/occc',
  serverExternalPackages: ['dockerode', 'ssh2'],
};

module.exports = nextConfig;
