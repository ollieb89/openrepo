import type { RemoteTransport, RemoteTransportConfig } from '@/lib/types/privacy';

const DEFAULT_TIMEOUT_MS = 10_000;

function validateTransportConfig(config: RemoteTransportConfig): URL {
  let endpoint: URL;
  try {
    endpoint = new URL(config.endpoint);
  } catch {
    throw new Error('Remote transport endpoint must be a valid URL.');
  }

  if (endpoint.protocol !== 'https:') {
    throw new Error('Remote transport endpoint must use HTTPS.');
  }

  if (config.tls?.rejectUnauthorized === false) {
    throw new Error('Insecure TLS configuration is not allowed for remote transport.');
  }

  return endpoint;
}

export function createRemoteTransport(config: RemoteTransportConfig): RemoteTransport {
  const endpoint = validateTransportConfig(config);

  return {
    async invoke(payload: unknown): Promise<unknown> {
      const controller = new AbortController();
      const timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'content-type': 'application/json',
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
          cache: 'no-store',
        });

        if (!response.ok) {
          throw new Error(`Remote transport failed with status ${response.status}.`);
        }

        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          return response.json();
        }

        return response.text();
      } finally {
        clearTimeout(timeoutId);
      }
    },
  };
}
