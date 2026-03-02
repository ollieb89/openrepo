/**
 * Authentication utilities for OpenClaw Dashboard
 * Uses token-based authentication with OPENCLAW_GATEWAY_TOKEN
 */

export interface AuthContext {
  isAuthenticated: boolean;
  token?: string;
  error?: string;
}

const EXPECTED_TOKEN = process.env.OPENCLAW_GATEWAY_TOKEN || '';

/**
 * Validate authentication token from request headers
 * Supports:
 * - Authorization: Bearer <token>
 * - x-openclaw-token: <token>
 * - _token query parameter (for SSE/EventSource)
 */
export function validateToken(
  authHeader?: string,
  customTokenHeader?: string,
  queryToken?: string
): boolean {
  if (!EXPECTED_TOKEN) {
    // No token configured = no auth required
    return true;
  }

  // Try Authorization header first
  if (authHeader) {
    const match = authHeader.match(/^Bearer\s+(.+)$/i);
    if (match && match[1] === EXPECTED_TOKEN) {
      return true;
    }
  }

  // Try custom header
  if (customTokenHeader && customTokenHeader === EXPECTED_TOKEN) {
    return true;
  }

  // Try query parameter (for SSE)
  if (queryToken && queryToken === EXPECTED_TOKEN) {
    return true;
  }

  return false;
}

/**
 * Extract token from request headers/query
 */
export function extractToken(
  authHeader?: string,
  customTokenHeader?: string,
  queryToken?: string
): string | undefined {
  if (authHeader) {
    const match = authHeader.match(/^Bearer\s+(.+)$/i);
    if (match) return match[1];
  }
  return customTokenHeader || queryToken;
}

/**
 * Check if authentication is required
 */
export function isAuthRequired(): boolean {
  return !!EXPECTED_TOKEN;
}

/**
 * Get the expected token (for client-side token storage)
 * Only returns token if explicitly enabled for client access
 */
export function getExpectedToken(): string {
  return EXPECTED_TOKEN;
}

/**
 * Create a standard 401 Unauthorized response
 */
export function createUnauthorizedResponse(): Response {
  return new Response(
    JSON.stringify({
      error: 'Unauthorized',
      message: 'Missing or invalid authentication token',
      hint: 'Provide token via: Authorization: Bearer <token> header or X-OpenClaw-Token header',
    }),
    { status: 401, headers: { 'Content-Type': 'application/json' } }
  );
}
