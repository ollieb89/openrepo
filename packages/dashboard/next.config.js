/** @type {import("next").NextConfig} */
const nextConfig = {
  basePath: '/occc',
  serverExternalPackages: ['dockerode', 'ssh2'],
  env: {
    // Expose OPENCLAW_ROOT as a build-time constant so the Environment page
    // can display the project root directory on the client side.
    OPENCLAW_ROOT: process.env.OPENCLAW_ROOT || '',
  },
};

module.exports = nextConfig;
