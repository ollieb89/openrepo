/**
 * Authenticated fetch utility
 * Automatically includes the authentication token in API requests
 */

import { useAuth } from '@/context/AuthContext';

export function useAuthenticatedFetch() {
  const { token } = useAuth();

  const authenticatedFetch = async (
    url: string,
    options: RequestInit & { skipAuth?: boolean } = {}
  ) => {
    const headers = new Headers(options.headers);

    // Add token to request if available and not skipped
    if (token && !options.skipAuth) {
      headers.set('X-OpenClaw-Token', token);
    }

    return fetch(url, {
      ...options,
      headers,
    });
  };

  return authenticatedFetch;
}
