/**
 * Centralized API client that handles the basePath configuration.
 * The dashboard uses basePath: '/occc' in next.config.js,
 * so all API calls must be prefixed with '/occc'.
 */

const BASE_PATH = '/occc';

// WebSocket server URL - set to empty to disable WebSocket connections
// The WebSocket server is optional - dashboard works fine without it
// Can be overridden via environment variable
// Note: WebSocket server does NOT use basePath - it's a separate server
const WS_SERVER_URL = process.env.NEXT_PUBLIC_WS_URL || '';  // Disabled by default to avoid console errors

/**
 * Get auth token from localStorage (client-side only)
 */
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('openclaw_token');
}

/**
 * Constructs a full API path with the basePath prefix.
 * @param path - The API path (e.g., '/api/projects')
 * @returns The full path with basePath (e.g., '/occc/api/projects')
 */
export function apiPath(path: string): string {
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${BASE_PATH}${normalizedPath}`;
}

/**
 * Constructs a WebSocket URL.
 * Note: WebSocket server runs on a separate port and does NOT use basePath.
 * @param path - The WebSocket endpoint path (e.g., '/events')
 * @returns The full WebSocket URL (e.g., 'ws://localhost:8080/events') or empty string if disabled
 */
export function wsUrl(path: string): string {
  // If WebSocket is disabled, return empty string
  if (!WS_SERVER_URL) {
    return '';
  }
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  // WebSocket server does NOT include basePath
  return `${WS_SERVER_URL}${normalizedPath}`;
}

/**
 * Wrapper around fetch that automatically prepends the basePath and adds auth token.
 * @param path - The API path
 * @param init - Fetch init options
 * @param skipAuth - Skip adding auth token (for public routes)
 * @returns Promise<Response>
 */
export function apiFetch(
  path: string, 
  init?: RequestInit,
  skipAuth = false
): Promise<Response> {
  const headers = new Headers(init?.headers);
  
  // Add auth token if available and not skipped
  if (!skipAuth) {
    const token = getAuthToken();
    if (token) {
      headers.set('X-OpenClaw-Token', token);
    }
  }
  
  return fetch(apiPath(path), {
    ...init,
    headers,
  });
}

/**
 * Helper for JSON API requests with automatic basePath handling.
 * @param path - The API path
 * @param init - Fetch init options
 * @param skipAuth - Skip adding auth token (for public routes)
 * @returns Promise with parsed JSON
 */
export async function apiJson<T>(
  path: string, 
  init?: RequestInit,
  skipAuth = false
): Promise<T> {
  const response = await apiFetch(path, init, skipAuth);
  
  if (response.status === 401) {
    // Redirect to login on auth failure
    if (typeof window !== 'undefined') {
      window.location.href = '/occc/login';
    }
    throw new Error('Authentication required');
  }
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  
  return response.json() as Promise<T>;
}
